create table user (
    pubkey text not null primary key,
    first_seen timestamp not null
);

create table wallet (
    pubkey text not null primary key,
    currency integer default 0 not null
);

create table stats (
    pubkey text not null primary key,
    winnings integer default 0 not null,
    games integer default 0 not null,
    wins integer default 0 not null,
    losses integer default 0 not null
);

create table session (
    pubkey text not null primary key,
    logged_in timestamp not null,
    host text not null,
    port integer not null
);

create table game_table (
    name text not null primary key,
    passphrase text,
    created timestamp not null,
    created_by_pubkey text not null,
    seats integer not null,
    buyin integer not null,
    small_blind integer not null,
    big_blind integet not null
);
