CREATE TABLE IF NOT EXISTS exp (
    GuildID integer PRIMARY KEY,
    UserID integer PRIMARY KEY,
    XP integer DEFAULT 0,
    Level integer DEFAULT 0,
    XPLock text DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS guild (
    GuildID integer PRIMARY KEY,
    HasPremium integer DEFAULT 0,
    HasBeta integer DEFAULT 0
);