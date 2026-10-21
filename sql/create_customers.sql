-- wh.CUSTOMERS — target table for CUSTOMER_MASTER.xlsx (SQL Server).
-- Sizes measured from the file (84,367 rows) with headroom; observed max length in comments.
-- ROUTE NAME / SERVICED BY are comma-joined rep lists (max 1006 chars) — the cause of the
-- original "String or binary data would be truncated" (8152) errors.

DROP TABLE IF EXISTS [wh].[CUSTOMERS];

CREATE TABLE [wh].[CUSTOMERS] (
    [Id]                      INT             NOT NULL PRIMARY KEY,  -- unique in file
    [CUSTOMER CODE]           NVARCHAR(50)    NULL,  -- 18
    [CUSTOMER NAME]           NVARCHAR(255)   NULL,  -- 68
    [CLASSIFICATION]          NVARCHAR(100)   NULL,  -- always empty
    [PHONE NUMBER]            NVARCHAR(50)    NULL,  -- 15
    [CUSTOMER CATEGORY]       NVARCHAR(100)   NULL,  -- 24
    [SUB CATEGORY]            NVARCHAR(100)   NULL,  -- 21
    [CUSTOMER TYPE]           NVARCHAR(50)    NULL,  -- 8
    [RELATION]                NVARCHAR(50)    NULL,  -- 8
    [LOCATION NAME]           NVARCHAR(150)   NULL,  -- 38
    [TERRITORY NAME]          NVARCHAR(150)   NULL,  -- always empty
    [ROUTE NAME]              NVARCHAR(4000)  NULL,  -- 1006
    [SUCCESSFUL VISITS]       INT             NULL,
    [REGION NAME]             NVARCHAR(50)    NULL,  -- 7
    [ACCOUNT NAME]            NVARCHAR(150)   NULL,  -- 10
    [SUPPLIER NAME]           NVARCHAR(150)   NULL,  -- 41
    [CHANNEL]                 NVARCHAR(50)    NULL,  -- 13
    [ADDED BY]                NVARCHAR(150)   NULL,  -- 31
    [SERVICED BY]             NVARCHAR(4000)  NULL,  -- 1006
    [SALES REP ID]            INT             NULL,
    [REP CATEGORY]            NVARCHAR(150)   NULL,  -- 31
    [REP CATEGORY CODE]       BIGINT          NULL,  -- up to 2003247013
    [VERIFICATION]            NVARCHAR(50)    NULL,  -- 8
    [VERIFIED BY]             NVARCHAR(150)   NULL,  -- 25
    [VERIFICATION DATE]       DATETIME2(3)    NULL,
    [EMAIL]                   NVARCHAR(255)   NULL,  -- 37
    [CONTACT PERSON]          NVARCHAR(255)   NULL,  -- 100
    [KRA PIN]                 NVARCHAR(50)    NULL,  -- 12
    [STATUS]                  NVARCHAR(50)    NULL,  -- 8
    [LATITUDE]                DECIMAL(10,7)   NULL,
    [LONGITUDE]               DECIMAL(10,7)   NULL,
    [ADDRESS]                 NVARCHAR(255)   NULL,  -- 35
    [FIRST SALE DATE]         DATETIME2(3)    NULL,
    [LAST SALE DATE]          DATETIME2(3)    NULL,
    [LAST SALE BY]            NVARCHAR(150)   NULL,  -- 31
    [LAST VISIT DATE]         DATETIME2(3)    NULL,
    [LAST VISIT BY]           NVARCHAR(150)   NULL,  -- 31
    [TOTAL VALUE]             DECIMAL(18,2)   NULL,  -- up to 395,464,942.48
    [TOTAL VISITS]            INT             NULL,
    [DATE CREATED]            DATETIME2(3)    NULL,
    [PARENT NAME]             NVARCHAR(150)   NULL,  -- 36
    [ADDITIONAL PHONE NUMBER] NVARCHAR(50)    NULL   -- 13
);
