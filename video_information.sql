CREATE TABLE video_information (
    id SERIAL PRIMARY KEY,
    video_name VARCHAR(90),
    video_duration INT,
    video_size INT,
    vehicle_count INT
);

INSERT INTO video_information (video_name, video_duration, video_size, vehicle_count)
VALUES ('test', 2, 400, 18);
