SELECT player_name, team_name, position, goals, appearances
FROM player_stats
ORDER BY goals DESC
LIMIT 15;
