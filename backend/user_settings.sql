CREATE TABLE user_settings (
    user_id VARCHAR(255),
    workspace_id VARCHAR(255),
    select_langage VARCHAR(255),
    report_channel_id VARCHAR(255),
    invoice_channel_id VARCHAR(255),
    database_id VARCHAR(255),
    supervisor_user_id VARCHAR(255),
    PRIMARY KEY (user_id, workspace_id)
)

CREATE TABLE punch_time (
    p_key INT IDENTITY(1,1),
    punch_user_id VARCHAR(255),
    punch_workspace_id VARCHAR(255),
    punch_date VARCHAR(255),
    punch_in VARCHAR(255),
    punch_out VARCHAR(255),
    work_time VARCHAR(255),
    work_contents VARCHAR(255),
    PRIMARY KEY (p_key)
);

CREATE TABLE break_time(
    break_id INT IDENTITY(1,1),
    punch_id INT,
    break_begin_time DATETIME,
    break_end_time DATETIME,
    break_duration INT,
    PRIMARY KEY (break_id),
    FOREIGN KEY (punch_id) REFERENCES punch_time(p_key)
);

CREATE TABLE user_status (
    user_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(255)
);