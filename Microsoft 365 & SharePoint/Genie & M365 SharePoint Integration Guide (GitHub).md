# Genie & Microsoft 365 / SharePoint Integration Guide

The step-by-step guide and code live in their own repository:

**➡️ [github.com/jason-miles/Genie-and-M365-SharePoint-Integration](https://github.com/jason-miles/Genie-and-M365-SharePoint-Integration)**

It covers three paths:

| Path | What it does |
|---|---|
| **A · Genie One + Microsoft 365** | Live search over SharePoint, Teams, Outlook and Calendar with each user's own permissions |
| **B · Lakeflow Connect SharePoint** | Managed ingestion of SharePoint files into governed Delta tables, then Knowledge Assistant or Vector Search |
| **C · Custom Microsoft Graph pipeline** | Delta-query ingestion with per-document ACL capture and security-trimmed retrieval |

The repository includes Terraform (Entra app with `Sites.Selected`, secrets, Unity Catalog, Vector Search), a Databricks Asset Bundle, tested notebooks, helper scripts and an end-to-end smoke test. Last updated 13 October 2026.
