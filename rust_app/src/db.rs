use anyhow::Context;
use rusqlite::{Connection, params};
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Session {
    pub start_time: String,
    pub end_time: String,
    pub duration_seconds: f64,
    pub download_mb: f64,
    pub upload_mb: f64,
    pub tracking_type: String,
    pub process_name: Option<String>,
}

#[derive(Debug, Clone)]
pub struct Stats {
    pub total_sessions: i64,
    pub total_time_seconds: f64,
    pub total_download_mb: f64,
    pub total_upload_mb: f64,
    pub avg_download_mb: f64,
    pub avg_upload_mb: f64,
}

#[derive(Debug, Clone)]
pub struct SpeedTestRow {
    pub test_time: String,
    pub download_mbps: f64,
    pub upload_mbps: f64,
    pub ping_ms: f64,
}

pub fn open_connection(db_path: &Path) -> anyhow::Result<Connection> {
    let conn = Connection::open(db_path)
        .with_context(|| format!("Failed to open database at {}", db_path.display()))?;
    init_database(&conn)?;
    Ok(conn)
}

fn init_database(conn: &Connection) -> anyhow::Result<()> {
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            download_mb REAL NOT NULL,
            upload_mb REAL NOT NULL,
            tracking_type TEXT NOT NULL,
            process_name TEXT
        );

        CREATE TABLE IF NOT EXISTS speed_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_time TEXT NOT NULL,
            download_mbps REAL NOT NULL,
            upload_mbps REAL NOT NULL,
            ping_ms REAL NOT NULL
        );
        "#,
    )?;

    Ok(())
}

pub fn insert_session(conn: &Connection, session: &Session) -> anyhow::Result<()> {
    conn.execute(
        r#"
        INSERT INTO sessions (
            start_time,
            end_time,
            duration_seconds,
            download_mb,
            upload_mb,
            tracking_type,
            process_name
        )
        VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
        "#,
        params![
            session.start_time,
            session.end_time,
            session.duration_seconds,
            session.download_mb,
            session.upload_mb,
            session.tracking_type,
            session.process_name
        ],
    )?;
    Ok(())
}

pub fn fetch_sessions(conn: &Connection) -> anyhow::Result<Vec<Session>> {
    let mut stmt = conn.prepare(
        r#"
        SELECT start_time, end_time, duration_seconds, download_mb, upload_mb, tracking_type, process_name
        FROM sessions
        ORDER BY start_time
        "#,
    )?;

    let rows = stmt.query_map([], |row| {
        Ok(Session {
            start_time: row.get(0)?,
            end_time: row.get(1)?,
            duration_seconds: row.get(2)?,
            download_mb: row.get(3)?,
            upload_mb: row.get(4)?,
            tracking_type: row.get(5)?,
            process_name: row.get(6)?,
        })
    })?;

    let sessions = rows.collect::<Result<Vec<_>, _>>()?;
    Ok(sessions)
}

pub fn fetch_stats(conn: &Connection) -> anyhow::Result<Option<Stats>> {
    let mut stmt = conn.prepare(
        r#"
        SELECT
            COUNT(*) as total_sessions,
            COALESCE(SUM(duration_seconds), 0),
            COALESCE(SUM(download_mb), 0),
            COALESCE(SUM(upload_mb), 0),
            COALESCE(AVG(download_mb), 0),
            COALESCE(AVG(upload_mb), 0)
        FROM sessions
        "#,
    )?;

    let mut rows = stmt.query([])?;
    if let Some(row) = rows.next()? {
        let total_sessions: i64 = row.get(0)?;
        if total_sessions == 0 {
            return Ok(None);
        }

        return Ok(Some(Stats {
            total_sessions,
            total_time_seconds: row.get(1)?,
            total_download_mb: row.get(2)?,
            total_upload_mb: row.get(3)?,
            avg_download_mb: row.get(4)?,
            avg_upload_mb: row.get(5)?,
        }));
    }

    Ok(None)
}

pub fn clear_sessions(conn: &Connection) -> anyhow::Result<()> {
    conn.execute("DELETE FROM sessions", [])?;
    Ok(())
}

pub fn insert_speed_test(conn: &Connection, row: &SpeedTestRow) -> anyhow::Result<()> {
    conn.execute(
        r#"
        INSERT INTO speed_tests (test_time, download_mbps, upload_mbps, ping_ms)
        VALUES (?1, ?2, ?3, ?4)
        "#,
        params![
            row.test_time,
            row.download_mbps,
            row.upload_mbps,
            row.ping_ms
        ],
    )?;
    Ok(())
}

pub fn session_count(conn: &Connection) -> anyhow::Result<i64> {
    let count = conn.query_row("SELECT COUNT(*) FROM sessions", [], |row| row.get(0))?;
    Ok(count)
}
