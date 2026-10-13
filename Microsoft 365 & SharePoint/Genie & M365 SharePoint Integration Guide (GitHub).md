# Genie & Microsoft 365 / SharePoint Integration Guide

The step-by-step guide and code live in their own repository:

**➡️ [github.com/jason-miles/Genie-and-M365-SharePoint-Integration](https://github.com/jason-miles/Genie-and-M365-SharePoint-Integration)**

It covers three paths:

| Path | What it does |
|---|---|
| **A · Genie One + Microsoft 365** | Live search over SharePoint, Teams, Outlook and Calendar with each user's own permissions |
| **B · Lakeflow Connect SharePoint** | Managed ingestion of SharePoint files into governed Delta tables, then Knowledge Assistant or Vector Search |
| **C · Custom Microsoft Graph pipeline** | Delta-query ingestion with per-document ACL capture and security-trimmed retrieval |

The repository includes Terraform (Entra app with `Sites.Selected`, secrets, Unity Catalog, Vector Search), a Databricks Asset Bundle, helper scripts, and notebooks tested on a Databricks workspace with a synthetic corpus, plus a smoke test for the ingest-and-search half of Paths B and C. Steps that need a Microsoft tenant (the SharePoint connection, Entra app, Graph API and Path A) are not yet tested; see the repository's "What has been tested" section. Last updated 13 October 2026.
