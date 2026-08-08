from predict_match import predict_match_outcome, get_available_teams


def main():
    print("=== Premier league match predictor ===")
    teams = get_available_teams()
    print("\nAvailable Teams: ")
    for team in teams:
        print(f" - {team}")

    print("\n" + "-"*40)
    home_input = input("Enter Home Team: ").strip()
    away_input = input("Enter Away Team: ").strip()
    print(f"Analyzing {home_input} vs {away_input}...")
    results = predict_match_outcome(home_input, away_input)
    print("\n--- PREDICTION RESULTS ---")
    print(f"Home Win ({home_input}): {results['Home Win']}%")
    print(f"Draw:                   {results['Draw']}%")
    print(f"Away Win ({away_input}): {results['Away Win']}%")


if __name__ == "__main__":
    main()
