"""Render the Azure ETL and chart-of-accounts diagrams (Graphviz). Process swimlanes are in diagrams/ already.
Run: python tools/make_diagrams.py   (requires the graphviz 'dot' binary)
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "diagrams"
G = ('fontname="Helvetica"; node[shape=box,style="rounded,filled",fontname="Helvetica",fontsize=10,fillcolor="#E8F0FA",color="#1F4E79"]; '
     'edge[color="#3A78C9",penwidth=1.4,fontname="Helvetica",fontsize=8.5,fontcolor="#8B1A1A"];')

DOTS = {
"etl_architecture": 'digraph G { rankdir=LR; nodesep=0.35; ranksep=0.55; compound=true; ' + G + '''
subgraph cluster_src { label="On-premises legacy"; fontname="Helvetica"; style=rounded; color="#999999";
  L1[label="Merchandising DB\\n(items, stores, vendors,\\nprices, on-hand)"]; L2[label="General ledger\\n(trial balance)"]; L3[label="POS back-office &\\nfile exports"]; IR[label="Self-hosted\\nintegration runtime",fillcolor="#F7E2A8",color="#B8933A"]; }
subgraph cluster_az { label="Microsoft Azure (private endpoints)"; fontname="Helvetica"; style=rounded; color="#3A78C9";
  ADF[label="Azure Data Factory\\norchestration · copy ·\\nDQ gate · run log",fillcolor="#C9DBF5",color="#5B7DB8"];
  subgraph cluster_lake { label="ADLS Gen2 data lake"; fontname="Helvetica"; style=rounded; color="#5E9A5E";
    B[label="bronze\\nraw Parquet\\nper run_id"]; S[label="silver\\ncleansed Delta"]; Gd[label="gold\\nSAP staging layout\\n(Delta)",fillcolor="#CFE8CF",color="#5E9A5E"]; }
  DBX[label="Azure Databricks\\nPySpark + retail_etl rules\\nGS1 · mappings · reconciliation",fillcolor="#C9DBF5",color="#5B7DB8"];
  SQL[label="Azure SQL control DB\\nobject catalogue · mappings ·\\nDQ & reconciliation results"]; KV[label="Key Vault\\nsecrets"]; PBI[label="Power BI\\nmigration dashboard"]; }
subgraph cluster_sap { label="SAP"; fontname="Helvetica"; style=rounded; color="#B0655A";
  STG[label="SAP HANA\\nMigration Cockpit\\nstaging tables",fillcolor="#F2CFCA",color="#B0655A"]; MC[label="Migration Cockpit\\nprepare · map ·\\nsimulate · migrate",fillcolor="#F2CFCA",color="#B0655A"]; S4[label="SAP S/4HANA Retail\\n(articles, sites, prices,\\nstock, G/L)",fillcolor="#F2CFCA",color="#B0655A"]; }
L1->IR; L2->IR; L3->IR; IR->ADF[label="extract"]; ADF->B[label="copy"]; B->S->Gd; DBX->S[style=dashed,arrowhead=none]; DBX->Gd[style=dashed,arrowhead=none];
ADF->DBX[label="notebooks"]; DBX->SQL[label="DQ /\\nrecon"]; SQL->PBI; KV->ADF[style=dashed]; KV->DBX[style=dashed];
Gd->STG[label="JDBC load\\n(truncate + insert)"]; STG->MC->S4; S4->ADF[label="OData control\\ntotals",style=dashed];
}''',
"etl_flow": 'digraph G { rankdir=TB; nodesep=0.3; ranksep=0.35; ' + G + '''
E[label="pl_10 Extract legacy → bronze (Parquet, run_id)"]; T1[label="01 Bronze → silver: trim, type, de-duplicate"];
T2[label="02 Silver → gold: mappings, generic/variant articles,\\nVKP0 prices, 561 stock, G/L mapping"]; Q[label="DQ gate: ERROR = 0 (cutover)\\nreconciliation = PASS",shape=diamond,fillcolor="#FFF2CC",color="#B8933A"];
FIX[label="Data owners fix in legacy\\n(Power BI DQ worklist)",fillcolor="#F2CFCA",color="#B0655A"]; L[label="pl_30 Load HANA staging tables\\n(load order 1 → 14)"];
MC[label="Migration Cockpit: prepare → map values →\\nsimulate → migrate",fillcolor="#F2CFCA",color="#B0655A"]; R[label="pl_40 Reconcile S/4 vs gold\\n(counts, stock qty & value, G/L)",fillcolor="#CFE8CF",color="#5E9A5E"];
E->T1->T2->Q; Q->L[label="pass"]; Q->FIX[label="fail"]; FIX->E[style=dashed,label="next run"]; L->MC->R;
}''',
"coa_structure": 'digraph G { rankdir=LR; nodesep=0.2; ranksep=0.4; ' + G + '''
C[label="Chart of accounts\\nYCOA-based (US10)",fillcolor="#FFF2CC",color="#B8933A"];
A[label="1 Assets\\ncash & tender clearing · vendor rebates ·\\ninventory · fixed assets · ROU"]; Li[label="2 Liabilities\\npayables · GR/IR · gift cards ·\\nrefund liability · tax · leases"];
Eq[label="3 Equity\\ncapital · retained earnings ·\\n39990000 migration clearing"]; R[label="4 Revenue\\nstore · online · returns ·\\ndiscounts · breakage"];
CO[label="5 Cost of goods sold\\nCOGS · price differences · shrinkage ·\\nrebate & markdown funding"]; O[label="6 Operating expenses\\npersonnel · occupancy · SG&A ·\\ncard fees · depreciation"];
F[label="7–8 Financial result & taxes"]; S[label="9 Secondary cost elements\\nDC & HQ assessment · activity allocation"];
C->A; C->Li; C->Eq; C->R; C->CO; C->O; C->F; C->S;
}''',
}
for name, src in DOTS.items():
    dot = OUT / f"{name}.dot"
    dot.write_text(src, encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=150", str(dot), "-o", str(OUT / f"{name}.png")], check=True)
    dot.unlink()
print("diagrams written")
