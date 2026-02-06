# 🍽️ Slim Weekmenu

Dutch-language weekly meal planner that generates diverse, healthy weekly menus from your recipe database.

## Features

- 🤖 AI-powered recipe extraction from PDFs and images using Google Gemini
- 📊 Smart menu generation with ingredient similarity scoring
- 🥗 Vegetable-focused healthy meal planning
- 🛒 Automatic shopping list generation with pantry exclusions
- 📄 PDF export for weekly menus and recipes
- 🎨 Interactive Streamlit web interface

## Quick Start (Streamlit Cloud)

The app is deployed at: [Your Streamlit Cloud URL will appear here]

No installation needed - just visit the URL and start planning meals!

## Local Development

### Prerequisites

- Python 3.8+
- Google Gemini API key (only for importing new recipes)

### Installation

```bash
# Clone repository
git clone https://github.com/KoenSteenhout/WeekMenu.git
cd WeekMenu

# Install dependencies
pip install -r requirements.txt

# Run the app
cd scripts
streamlit run app.py
```

### Import Recipes (Optional)

If you want to import new recipes:

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set the environment variable:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
3. Run import scripts:
   ```bash
   cd scripts
   # Import from PDFs
   python import_pdfs.py
   # Or import from scanned images
   python batch_ocr.py
   python import_json.py
   ```

## Project Structure

```
WeekMenuPython/
├── scripts/
│   ├── app.py                 # Streamlit web interface
│   ├── generate_menu.py       # Core menu generation logic
│   ├── db.py                  # Database schema & helpers
│   ├── import_pdfs.py         # PDF recipe import
│   ├── import_json.py         # JSON recipe import
│   ├── batch_ocr.py           # Batch OCR for images
│   └── gemini_extract.py      # Gemini API wrapper
├── data/
│   ├── recipes.db             # SQLite recipe database
│   └── pantry.json            # Pantry items configuration
├── pdf/                       # PDF cookbooks (for import)
├── scans/                     # Scanned recipe cards (for import)
└── ocr/                       # OCR results (JSON)
```

## How It Works

1. **Recipe Storage**: Recipes are stored in SQLite with ingredients, steps, and metadata
2. **Menu Generation**: Algorithm selects 7 diverse recipes based on:
   - Ingredient similarity (promotes ingredient reuse)
   - Title uniqueness (avoids near-duplicates)
   - Cooking method diversity (no consecutive pasta/curry nights)
   - Vegetable content (promotes healthy meals)
   - Recipe complexity balance
3. **Shopping List**: Aggregates ingredients, scales to 4 servings, excludes pantry items
4. **PDF Export**: Generates formatted PDF with menu, shopping list, and full recipes

## Configuration

- **Target servings**: 4 (default, configurable in `generate_menu.py`)
- **Pantry items**: Managed via web UI or `data/pantry.json`
- **Vegetable variety target**: 15+ unique vegetables per week
- **Similarity threshold**: 0.75 for title matching

## Tech Stack

- **Frontend**: Streamlit
- **Database**: SQLite
- **AI**: Google Gemini 2.5 Flash
- **PDF**: ReportLab
- **OCR**: PyMuPDF + Gemini Vision

## License

Personal project - feel free to adapt for your own use.

## Credits

Built with Claude Code (Anthropic) 🤖
