import os
import requests
import datetime
from together import Together
from dotenv import load_dotenv
from fpdf import FPDF

# Load API keys from .env file
load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Initialize Together AI client
client = Together(api_key=TOGETHER_API_KEY)

def get_company_news(company_name, num_days=10):
    """
    Fetch news articles using NewsAPI with filters:
     - Date range: last num_days
     - Language: English only
     - And force results to be India-centric by including 'India' in the query.
    """
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=num_days)
    
    # Query forces results to be relevant to India if the company is Indian.
    query = f"{company_name} AND India"
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "language": "en",
        "sortBy": "popularity",
        "apiKey": NEWS_API_KEY
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("Error fetching news from NewsAPI.")
        return []
    
    data = response.json()
    if data.get("status") != "ok":
        print("NewsAPI did not return a successful response.")
        return []
    
    articles = data.get("articles", [])
    if not articles:
        print("No news found for the specified company and date range.")
    return articles

def summarize_article(article):
    """
    Summarise a news article using DeepSeek R1.
    The prompt instructs the LLM to provide a 2–3 sentence summary in simple language,
    highlight key news points useful for traders or stock brokers,
    and not include any internal 'thinking' or analysis text.
    """
    article_text = (
        f"Title: {article.get('title', 'N/A')}\n"
        f"Description: {article.get('description', 'N/A')}\n"
        f"Content: {article.get('content', 'N/A')}\n"
        f"URL: {article.get('url', '')}\n"
        f"PublishedAt: {article.get('publishedAt', 'N/A')}"
    )
    
    prompt = (
        "Please summarise the following news article in 2-3 simple sentences. "
        "Highlight the key news points that a trader or stock broker might use to assess investment potential. "
        "Explain any technical term in brackets () and do not include any internal analysis or 'thinking' text.\n\n"
        f"{article_text}"
    )
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant providing investment insights by summarising news articles in simple language."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    summary_text = ""
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
                summary_text += token.choices[0].delta.content
    except Exception as e:
        summary_text = f"Error during summarisation: {e}"
    
    return summary_text.strip()

def generate_pdf(company_name, news_data):
    """
    Generate a PDF file (companyname.pdf) with a table of news data.
    Each article includes: Published Date, Source, Title, Summary, and URL.
    Uses a Unicode font to support all characters.
    """
    pdf = FPDF()
    pdf.add_page()

    # Add a Unicode font. If you have DejaVuSans.ttf, place it in the same directory.
    # If you don't have a bold version, we'll use the regular style.
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        # Try using the same font for bold.
        pdf.add_font('DejaVu', 'B', 'DejaVuSans.ttf', uni=True)
        pdf.set_font("DejaVu", "B", 16)
    except Exception as e:
        raise RuntimeError("PDF font error: " + str(e))

    pdf.cell(0, 10, f"{company_name} - Investment News Insights", ln=True, align="C")
    pdf.ln(5)

    # Set headers and column widths
    headers = ["Date", "Source", "Title", "Summary", "URL"]
    col_widths = [25, 30, 50, 80, 30]  # Adjust widths as needed
    
    # Header row
    pdf.set_font("DejaVu", "B", 12)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)
    pdf.ln()

    # Data rows
    pdf.set_font("DejaVu", "", 10)
    for item in news_data:
        row = [
            item.get("publishedAt", "N/A")[:10],  # Only date part
            item.get("source", "Unknown"),
            item.get("title", "N/A"),
            item.get("summary", "N/A"),
            item.get("url", "")
        ]
        # Print each cell; use multi_cell for long text if needed.
        cell_y = pdf.get_y()
        max_height = 10
        for i, data in enumerate(row):
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(col_widths[i], 10, data, border=1)
            pdf.set_xy(x + col_widths[i], y)
            max_height = max(max_height, pdf.get_y() - y)
        pdf.ln(max_height)
    
    output_filename = f"{company_name}.pdf"
    pdf.output(output_filename)
    print(f"PDF generated: {output_filename}")

def generate_html(company_name, news_data):
    """
    Generate an HTML file (companyname.html) with a table of news data.
    Each article includes: Published Date, Source, Title, Summary, and URL.
    """
    output_filename = f"{company_name}.html"
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{company_name} - Investment News Insights</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 20px;
}}
table {{
    border-collapse: collapse;
    width: 100%;
}}
th, td {{
    border: 1px solid #ddd;
    padding: 8px;
}}
th {{
    background-color: #f2f2f2;
    text-align: left;
}}
</style>
</head>
<body>
<h2>{company_name} - Investment News Insights</h2>
<table>
<tr>
<th>Date</th>
<th>Source</th>
<th>Title</th>
<th>Summary</th>
<th>URL</th>
</tr>
"""
    for item in news_data:
        publishedAt = item.get("publishedAt", "N/A")[:10]
        source = item.get("source", "Unknown")
        title = item.get("title", "N/A")
        summary = item.get("summary", "N/A")
        url = item.get("url", "")
        html_content += f"<tr><td>{publishedAt}</td><td>{source}</td><td>{title}</td><td>{summary}</td><td><a href='{url}'>Link</a></td></tr>"
    
    html_content += """
</table>
</body>
</html>
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML generated: {output_filename}")

def main():
    company = input("Enter company name: ")
    try:
        days = int(input("Enter number of days to look back: "))
    except ValueError:
        print("Invalid number of days. Using default of 10 days.")
        days = 10
    
    print("Fetching news articles...")
    articles = get_company_news(company, days)
    if not articles:
        print("No news found. Exiting.")
        return
    
    news_data = []
    print("Summarising news articles...")
    for article in articles:
        summary = summarize_article(article)
        news_data.append({
            "publishedAt": article.get("publishedAt", "N/A"),
            "source": article.get("source", {}).get("name", "Unknown"),
            "title": article.get("title", "N/A"),
            "summary": summary,
            "url": article.get("url", "")
        })
    
    print("Generating PDF with investment insights...")
    try:
        generate_pdf(company, news_data)
    except Exception as e:
        print("PDF generation failed:", e)
        print("Falling back to HTML output...")
        generate_html(company, news_data)

if __name__ == "__main__":
    main()
