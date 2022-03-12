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