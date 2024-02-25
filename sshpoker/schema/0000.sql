create table user (
    pubkey text not null primary key,
    display_name text not null,
    first_seen timestamp not null
);

create table user_stats (
    pubkey text not null primary key,
    winnings integer default 0,
    games integer default 0,
    wins integer default 0,
    losses integer default 0
);
