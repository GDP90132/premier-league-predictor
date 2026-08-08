WITH match_features AS (
    SELECT 
        id, 
        utcDate,
        "homeTeam.id" AS home_team_id, 
        "awayTeam.id" AS away_team_id, 
        "homeTeam.name" AS home_name,
        "awayTeam.name" AS away_name,
        




        -- 1. Home Team: Goals Scored
        AVG("score.fullTime.home") OVER (
            PARTITION BY "homeTeam.id" 
            ORDER BY utcDate 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS Home_Team_AvgGoals,

        -- 2. Home Team: Goals Conceded
        AVG("score.fullTime.away") OVER (
            PARTITION BY "homeTeam.id" 
            ORDER BY utcDate 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS Home_Team_AvgConceded,

        -- 3. Away Team: Goals Scored
        AVG("score.fullTime.away") OVER (
            PARTITION BY "awayTeam.id" 
            ORDER BY utcDate 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS Away_Team_AvgGoals,

        -- 4. Away Team: Goals Conceded
        AVG("score.fullTime.home") OVER (
            PARTITION BY "awayTeam.id" 
            ORDER BY utcDate 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
            ) AS Away_Team_AvgConceded,

        CASE 
            WHEN "score.fullTime.home" > "score.fullTime.away" THEN 1
            WHEN "score.fullTime.home" = "score.fullTime.away" THEN 0 
            ELSE 2
        END AS target,

        SUM(
            CASE 
            WHEN "score.fullTime.home" > "score.fullTime.away" THEN 3
            WHEN "score.fullTime.home" = "score.fullTime.away" THEN 1 
            ELSE 0
        END) OVER(
            PARTITION BY "homeTeam.id"
            ORDER BY utcDate
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS Home_Team_Form,


        SUM(
            CASE 
            WHEN "score.fullTime.away" > "score.fullTime.home" THEN 3
            WHEN "score.fullTime.away" = "score.fullTime.home" THEN 1 
            ELSE 0
        END) OVER(
            PARTITION BY "awayTeam.id"
            ORDER BY utcDate
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS Away_Team_Form

    FROM MATCHES
)
SELECT id,
    utcDate,
    home_team_id,
    away_team_id,
    Home_Team_AvgGoals,
    Away_Team_AvgGoals,
    Home_Team_AvgConceded,
    Away_Team_AvgConceded,
    Home_Team_Form,
    Away_Team_Form,
    target,
    home_name,
    away_name,
    
    -- Differences
    (Home_Team_AvgGoals - Away_Team_AvgGoals) AS goal_attack_diff,
    (Home_Team_AvgConceded - Away_Team_AvgConceded) AS goal_conceded_diff,
    (Home_Team_Form - Away_Team_Form) AS form_diff

FROM match_features
WHERE Home_Team_AvgGoals IS NOT NULL AND Away_Team_AvgGoals IS NOT NULL
ORDER BY utcDate;