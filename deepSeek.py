import os
import requests
import datetime
from together import Together
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load API keys from .env file
load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Initialize Together AI client
client = Together(api_key=TOGETHER_API_KEY)

def get_company_news(company_name, num_days=10):
    """
    Fetches news articles for the company using NewsAPI.
    """
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=num_days)

    news_api_url = "https://newsapi.org/v2/everything"
    params = {
        "q": company_name,
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "sortBy": "popularity",
        "apiKey": NEWS_API_KEY
    }
    response = requests.get(news_api_url, params=params)

    if response.status_code != 200:
        print("Error fetching news from NewsAPI.")
        return []

    data = response.json()
    if data.get("status") != "ok":
        print("NewsAPI did not return a successful response.")
        return []

    articles = data.get("articles", [])
    if not articles:
        print("No news found for the given query and date range.")
    return articles

def summarize_news(news_articles):
    """
    Sends each news article to DeepSeek R1 LLM to summarise and analyze it.
    The prompt instructs the LLM to use simple language, explain technical terms in brackets (),
    include the important points, and indicate if the news is good or bad for the company's financial health.
    Also, the LLM's internal thinking process is included in the response.
    """
    summaries = []

    for article in news_articles:
        # Combine available details of the article
        article_text = (
            f"Title: {article.get('title', 'N/A')}\n"
            f"Description: {article.get('description', 'N/A')}\n"
            f"Content: {article.get('content', 'N/A')}\n"
            f"URL: {article.get('url', '')}\n"
            f"PublishedAt: {article.get('publishedAt', 'N/A')}"
        )

        prompt = (
            "Please analyse the following news article and summarise it in 2-3 sentences using simple language. "
            "Highlight the key points and explain if this news is good or bad for the company's financial health. "
            "If any technical term appears, please explain it in brackets (). Also, include your thinking process "
            "(i.e. your analysis and reasoning) in your output.\n\n"
            f"{article_text}"
        )

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant summarising financial news for market research in simple language."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Call DeepSeek R1 LLM and collect the streaming response
        response_text = ""
        try:
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                top_p=1,
                top_k=60,
                repetition_penalty=2,
                stop=["<｜end▁of▁sentence｜>"],
                stream=True
            )
            for token in response:
                if hasattr(token, 'choices'):
                    response_text += token.choices[0].delta.content
        except Exception as e:
            response_text = f"Error during summarisation: {e}"

        summaries.append({
            "title": article.get("title", "N/A"),
            "publishedAt": article.get("publishedAt", "N/A"),
            "source": article.get("source", {}).get("name", "Unknown"),
            "summary": response_text.strip(),
            "url": article.get("url", "")
        })

    return summaries

def display_news(news_summaries):
    """
    Displays the summarised news in a structured table.
    """
    console = Console()
    table = Table(title="Company News Analysis", show_header=True, header_style="bold magenta")

    table.add_column("Date", style="dim", width=12)
    table.add_column("Source", style="cyan", width=15)
    table.add_column("Title", style="bold", width=40)
    table.add_column("Analysis (Summary & Thinking)", style="white", width=80)

    for news in news_summaries:
        # Combine the summary and include the URL for reference
        combined_text = f"{news['summary']}\n\n[link={news['url']}]Read More[/link]"
        table.add_row(news["publishedAt"], news["source"], news["title"], combined_text)

    console.print(table)

if __name__ == "__main__":
    company = input("Enter company name: ")
    try:
        days = int(input("Enter number of days to look back: "))
    except ValueError:
        print("Invalid number of days. Using default of 10 days.")
        days = 10

    print("Fetching news articles...")
    news_articles = get_company_news(company, days)
    if not news_articles:
        print("No news found for the specified company and date range.")
    else:
        print("Summarising and analysing news articles...")
        news_summaries = summarize_news(news_articles)
        display_news(news_summaries)
