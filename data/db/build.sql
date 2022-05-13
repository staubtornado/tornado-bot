CREATE TABLE IF NOT EXISTS experience (
    GuildID integer,
    UserID integer,
    XP integer DEFAULT 0,
    Level integer DEFAULT 0,
    Messages integer DEFAULT 0,
    PRIMARY KEY (GuildID, UserID)
);

CREATE TABLE IF NOT EXISTS guilds (
    GuildID integer PRIMARY KEY,
    HasPremium integer DEFAULT 0,
    HasBeta integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS keys (
    KeyString message_text PRIMARY KEY,
    EnablesPremium integer,
    EnablesBeta integer
);

CREATE TABLE IF NOT EXISTS wallets (
    UserID integer PRIMARY KEY,
    Balance integer DEFAULT 0,
    Revenue integer DEFAULT 0,
    LastModified message_text DEFAULT NULL,
    GlobalTransactions integer DEFAULT 0,
    Fee REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subjects (
    GuildID integer,
    Subject integer,
    Seller integer,
    Price integer,
    Added message_text,
    PRIMARY KEY (GuildID, Subject)
);

CREATE TABLE IF NOT EXISTS settings (
    GuildID integer PRIMARY KEY,
--  Experience
    ExpIsActivated integer DEFAULT 0,
    ExpMultiplication REAL DEFAULT 1,
--  Music
    MusicEmbedSize integer DEFAULT 2,
--  Tickets
    TicketsCreateVoiceChannel integer DEFAULT 0,
    TicketsSupportRoleID integer,
    TicketsCategoryID integer
)