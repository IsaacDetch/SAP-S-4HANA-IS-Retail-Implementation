// Azure landing zone for the IS-Retail data migration ETL (one deployment per environment: dev / qa / prod).
// Deploy:  az deployment group create -g rg-retail-mig-dev -f etl/infra/main.bicep -p etl/infra/parameters.dev.json
targetScope = 'resourceGroup'

@description('Short environment name: dev, qa, prod')
param env string = 'dev'
param location string = resourceGroup().location
@description('Entra ID object id of the migration admins group (SQL admin, Key Vault officer)')
param adminGroupObjectId string
param adminGroupName string = 'grp-retail-migration-admins'

var suffix = 'retailmig${env}'

// ---------- Monitoring ----------
resource law 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${suffix}'
  location: location
  properties: { retentionInDays: 90, sku: { name: 'PerGB2018' } }
}

// ---------- Data lake (bronze / silver / gold / archive) ----------
resource lake 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${suffix}'
  location: location
  sku: { name: 'Standard_ZRS' }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'          // private endpoints only
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}
resource blobSvc 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: lake
  name: 'default'
  properties: { deleteRetentionPolicy: { enabled: true, days: 30 } }
}
resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for c in ['bronze', 'silver', 'gold', 'archive']: {
  parent: blobSvc
  name: c
}]

// ---------- Key Vault (legacy, SQL, HANA and S/4 credentials) ----------
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${suffix}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Disabled'
  }
}

// ---------- Azure SQL: migration control database ----------
resource sql 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: 'sql-${suffix}'
  location: location
  properties: {
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
      login: adminGroupName
      sid: adminGroupObjectId
      tenantId: subscription().tenantId
      principalType: 'Group'
    }
  }
}
resource sqlDb 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sql
  name: 'sqldb-migration-control'
  location: location
  sku: { name: 'GP_S_Gen5_2', tier: 'GeneralPurpose' }      // serverless – pauses between mock loads
  properties: { autoPauseDelay: 60, minCapacity: json('0.5') }
}

// ---------- Data Factory (orchestration; self-hosted IR is registered on-premises) ----------
resource adf 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: 'adf-${suffix}'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: { publicNetworkAccess: 'Disabled' }
}
resource shir 'Microsoft.DataFactory/factories/integrationRuntimes@2018-06-01' = {
  parent: adf
  name: 'shir-onprem'
  properties: { type: 'SelfHosted', description: 'Runs in the data center: legacy SQL Server, file shares, SAP HANA ODBC (alternative route)' }
}

// ---------- Databricks (transformations) with managed identity to the lake ----------
resource dbxConnector 'Microsoft.Databricks/accessConnectors@2023-05-01' = {
  name: 'dbac-${suffix}'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {}
}
resource dbx 'Microsoft.Databricks/workspaces@2023-02-01' = {
  name: 'dbw-${suffix}'
  location: location
  sku: { name: 'premium' }        // premium: Unity Catalog, cluster policies, secret ACLs
  properties: {
    managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', 'rg-dbw-${suffix}-managed')
    publicNetworkAccess: 'Disabled'
    requiredNsgRules: 'NoAzureDatabricksRules'
  }
}

// ---------- Role assignments ----------
var blobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'   // Storage Blob Data Contributor
var kvSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'     // Key Vault Secrets User
resource adfLake 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: lake
  name: guid(lake.id, adf.id, blobContributor)
  properties: { principalId: adf.identity.principalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributor) }
}
resource dbxLake 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: lake
  name: guid(lake.id, dbxConnector.id, blobContributor)
  properties: { principalId: dbxConnector.identity.principalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributor) }
}
resource adfKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: kv
  name: guid(kv.id, adf.id, kvSecretsUser)
  properties: { principalId: adf.identity.principalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUser) }
}

// ---------- Diagnostics to Log Analytics ----------
resource adfDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: adf
  name: 'to-law'
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output storageAccount string = lake.name
output dataFactory string = adf.name
output databricksUrl string = dbx.properties.workspaceUrl
output sqlServer string = sql.properties.fullyQualifiedDomainName
output keyVault string = kv.name
