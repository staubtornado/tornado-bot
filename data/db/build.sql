CREATE TABLE IF NOT EXISTS guilds (
    GuildID INTEGER PRIMARY KEY,
--  Beta / Premium
    HasBetaFeatures INTEGER DEFAULT 0,
    HasPremium INTEGER DEFAULT 0,
--  Experience
    XPIsActivated INTEGER DEFAULT 0,
    XPMultiplier INTEGER DEFAULT 1,
--  Music
    MusicEmbedSize INTEGER DEFAULT 2,
    RefreshMusicEmbed INTEGER DEFAULT 0,
--  Audit-Log
    GenerateAuditLog INTEGER DEFAULT 0,
    AuditLogChannel INTEGER DEFAULT NULL,
    WelcomeMessage INTEGER DEFAULT 0,
--  AutoMod
    AutoModLevel INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experience (
    GuildID INTEGER,
    UserID INTEGER,
    XP INTEGER DEFAULT 0,
    Messages INTEGER DEFAULT 0,
    PRIMARY KEY (GuildID, UserID)
);

CREATE TABLE IF NOT EXISTS keys (
    KeyString TEXT PRIMARY KEY,
    EnablesPremium INTEGER,
    EnablesBeta INTEGER
);
