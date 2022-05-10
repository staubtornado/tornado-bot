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

CREATE TABLE IF NOT EXISTS ticket_settings (
    GuildID integer PRIMARY KEY,
    CreateVoiceChannel integer DEFAULT 0,
    RoleID message_text,
    CategoryID integer
);

CREATE TABLE IF NOT EXISTS keys (
    KeyString message_text PRIMARY KEY,
    EnablesPremium integer,
    EnablesBeta integer
);

CREATE TABLE IF NOT EXISTS wallets (
    UserID integer PRIMARY KEY,
    Balance integer,
    Revenue integer,
    LastModified integer,
    GlobalTransactions integer
);