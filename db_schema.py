# TODO:task and crawl have different, non-overlapping columns across versions.
# xpath, site_visits, CrawlHistory, http_redirects has one version only
# flash cookies, profile_cookies has page_url/visit_id difference
# content_policy, pages: no table


DB_SCHEMA_HTTP_REQUESTS = """
    CREATE TABLE IF NOT EXISTS http_requests(
        id INTEGER PRIMARY KEY,
        crawl_id INTEGER NOT NULL,
        visit_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        top_level_url TEXT,
        method TEXT NOT NULL,
        referrer TEXT NOT NULL,
        headers TEXT NOT NULL,
        channel_id TEXT,
        is_XHR BOOLEAN,
        is_frame_load BOOLEAN,
        is_full_page BOOLEAN,
        is_third_party_channel BOOLEAN,
        is_third_party_window BOOLEAN,
        triggering_origin TEXT,
        loading_origin TEXT,
        loading_href TEXT,
        req_call_stack TEXT,
        content_policy_type INTEGER,
        post_body TEXT,
        time_stamp TEXT NOT NULL
    );
    """

DB_SCHEMA_HTTP_RESPONSES = """
    CREATE TABLE IF NOT EXISTS http_responses(
        id INTEGER PRIMARY KEY,
        crawl_id INTEGER NOT NULL,
        visit_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        method TEXT NOT NULL,
        referrer TEXT NOT NULL,
        response_status INTEGER NOT NULL,
        response_status_text TEXT NOT NULL,
        is_cached BOOLEAN,
        headers TEXT NOT NULL,
        channel_id TEXT,
        location TEXT NOT NULL,
        time_stamp TEXT NOT NULL,
        content_hash TEXT
    );
    """

DB_SCHEMA_JAVASCRIPT = """
    CREATE TABLE IF NOT EXISTS javascript(
        id INTEGER PRIMARY KEY,
        crawl_id INTEGER,
        visit_id INTEGER,
        script_url TEXT,
        script_line TEXT,
        script_col TEXT,
        func_name TEXT,
        script_loc_eval TEXT,
        document_url TEXT,
        top_level_url TEXT,
        call_stack TEXT,
        symbol TEXT,
        operation TEXT,
        value TEXT,
        arguments TEXT,
        time_stamp TEXT NOT NULL
    );
    """

DB_SCHEMA_JAVASCRIPT_COOKIES = """
    CREATE TABLE IF NOT EXISTS javascript_cookies(
        id INTEGER PRIMARY KEY ASC,
        crawl_id INTEGER,
        visit_id INTEGER,
        change TEXT,
        creationTime DATETIME,
        expiry DATETIME,
        is_http_only INTEGER,
        is_session INTEGER,
        last_accessed DATETIME,
        raw_host TEXT,
        expires INTEGER,
        host TEXT,
        is_domain INTEGER,
        is_secure INTEGER,
        name TEXT,
        path TEXT,
        policy INTEGER,
        status INTEGER,
        value TEXT
  );
  """

TABLE_SCHEMAS = {"http_requests": DB_SCHEMA_HTTP_REQUESTS,
                 "http_responses": DB_SCHEMA_HTTP_RESPONSES,
                 "javascript": DB_SCHEMA_JAVASCRIPT,
                 "javascript_cookies": DB_SCHEMA_JAVASCRIPT_COOKIES
                 }
