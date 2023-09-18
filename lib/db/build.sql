CREATE TABLE IF NOT EXISTS EmojiGuilds (
    guildId INTEGER NOT NULL,
    PRIMARY KEY (guildId)
);

CREATE TABLE IF NOT EXISTS Emojis (
    name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    isAnimated INTEGER NOT NULL DEFAULT 0,
    guildId INTEGER NOT NULL,
    PRIMARY KEY (name)
);

CREATE TABLE IF NOT EXISTS Leveling (
    guildId INTEGER NOT NULL,
    userId INTEGER NOT NULL,
    xp INTEGER NOT NULL DEFAULT 0,
    messageCount INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guildId, userId)
);


CREATE TABLE IF NOT EXISTS GuildSettings (
    guildId INTEGER NOT NULL,
    betaFeatures INTEGER NOT NULL DEFAULT 0,
    premium INTEGER NOT NULL DEFAULT 0,

    xpActive INTEGER NOT NULL DEFAULT 1,
    xpMultiplier INTEGER NOT NULL DEFAULT 1,

    musicEmbedSize INTEGER NOT NULL DEFAULT 0,

    logChannel INTEGER DEFAULT 0,
    sendWelcomeMessage INTEGER NOT NULL DEFAULT 0,
    welcomeMessage TEXT NOT NULL DEFAULT '**Hello** {user}! **Welcome** to **{guild}**!',
    PRIMARY KEY (guildId)
);


CREATE TABLE IF NOT EXISTS UserStats (
    userId INTEGER NOT NULL,
    commandsUsed INTEGER NOT NULL DEFAULT 0,
    musicPlayed INTEGER NOT NULL DEFAULT 0,
    songsPlayed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (userId)
);