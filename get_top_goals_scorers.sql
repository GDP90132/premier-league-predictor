SELECT player_name, team_name, position, goals, appearances
FROM player_stats
WHERE goals IS NOT NULL AND goals != ''
ORDER BY CAST(goals AS INTEGER) DESC
LIMIT 15;