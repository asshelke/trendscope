from utils import write_to_json, read_from_json, ask_chatgpt

SUMMARIZER_SYSTEM_ROLE = """
    You are a summarizing assistant. Your task is to summarize the latest trends 
    from X. You will be given a list of tweets for a particular trend, and
    your task is to provide a quality summmary of just that trend. You should 
    make sure to make each summary unique and straight to the point. Avoid 
    mentioning trend or X as much as possible. Do not use quotes or any special 
    characters.
"""

def summarize_trends(trend_data):
    trend_summaries = {}
    for rank, trend in trend_data.items():
        tweets = []
        for tweet in trend["tweets"]:
            tweets.append(tweet["text"])
        prompt = f"""
            A trend on X right now is called {trend["title"]}. Please summarize 
            this trend with this list of the top tweets given as a list of 
            strings in about 100 words: {tweets}
        """
        trend_summaries[rank] = ask_chatgpt(prompt, SUMMARIZER_SYSTEM_ROLE)[0]
    print("All trends succesfully summarized.")
    return trend_summaries
    
if __name__ == "__main__":
    trend_summaries = summarize_trends(read_from_json("additional_data.json")["data"])
    write_to_json(trend_summaries, "trend_summaries.json")