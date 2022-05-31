CREATE TABLE IF NOT EXISTS experience (
    GuildID INTEGER,
    UserID INTEGER,
    XP INTEGER DEFAULT 0,
    Level INTEGER DEFAULT 0,
    Messages INTEGER DEFAULT 0,
    PRIMARY KEY (GuildID, UserID)
);

CREATE TABLE IF NOT EXISTS guilds (
    GuildID INTEGER PRIMARY KEY,
    HasPremium INTEGER DEFAULT 0,
    HasBeta INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS keys (
    KeyString TEXT PRIMARY KEY,
    EnablesPremium INTEGER,
    EnablesBeta INTEGER
);

CREATE TABLE IF NOT EXISTS wallets (
    UserID INTEGER PRIMARY KEY,
    Balance INTEGER DEFAULT 0,
    Revenue INTEGER DEFAULT 0,
    LastModified TEXT DEFAULT NULL,
    GlobalTransactions INTEGER DEFAULT 0,
    Fee REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subjects (
    GuildID INTEGER,
    Subject INTEGER,
    Seller INTEGER,
    Price INTEGER,
    Added TEXT,
    PRIMARY KEY (GuildID, Subject)
);

CREATE TABLE IF NOT EXISTS companies (
    IndexInList INTEGER PRIMARY KEY,
    SharePrice INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    GuildID INTEGER PRIMARY KEY,
--  Experience
    ExpIsActivated INTEGER DEFAULT 0,
    ExpMultiplication REAL DEFAULT 1,
--  Music
    MusicEmbedSize INTEGER DEFAULT 2,
    MusicDeleteEmbedAfterSong INTEGER DEFAULT 0,
--  Tickets
    TicketsCreateVoiceChannel INTEGER DEFAULT 0,
    TicketsSupportRoleID INTEGER,
    TicketsCategoryID INTEGER
)