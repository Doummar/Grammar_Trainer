# Grammar Trainer Add-on

A professional, Qt6-compatible Anki add-on to automatically generate grammar cloze-dropdown exercises directly inside your cards using Gemini AI.

## Installation Instructions

### Method 1: Direct Folder Copy (Easiest & Fastest)
1. Open **Anki**.
2. Go to the top menu bar and select **Tools -> Add-ons**.
3. In the Add-ons manager, click the **View Files** button. This opens Anki's local add-ons directory in your file manager.
4. Create a new folder named `ai_grammar_dropdown` inside that directory.
5. Unzip all the files in this downloadable pack directly inside that newly created `ai_grammar_dropdown` folder.
6. **Restart Anki**.

### Method 2: Package as .ankiaddon
1. Select all files in this directory (`manifest.json`, `__init__.py`, `settings.py`, etc.) and add them to a standard **ZIP archive**.
2. Rename the extension of the resulting zip file from `.zip` to `.ankiaddon` (e.g., `ai_grammar_dropdown.ankiaddon`).
3. Inside Anki, select **Tools -> Add-ons**, then drag and drop the `.ankiaddon` file directly onto the add-ons list, or click **Install from file** and select the `.ankiaddon` file.
4. **Restart Anki**.

---

## How to Use

1. **Setup your API Key**:
   - Inside Anki, go to **Tools -> Grammar Trainer**.
   - Paste your **Gemini API key** and select your preferred default language and difficulty tier. Click **Save**.
   
   > 💡 **How to Get a 100% Free API Key (For Students):**
   > 1. Go to **Google AI Studio** (https://aistudio.google.com/) and sign in with any standard Google/Gmail account.
   > 2. Click **Get API Key** and click **Create API Key**.
   > 
   > 🇪🇺 / 🇬🇧 **If you are in Europe/EEA/UK:** Google disables the completely free tier (Quota Limit: 0) in European regions due to local regulations. 
   > To get it 100% free, simply connect a **VPN** to the **United States** (or another non-EU country) before creating your API key and while using the generator inside Anki. This bypasses the region restriction and grants you standard free access! Alternatively, adding a Pay-As-You-Go billing profile is extremely cheap (generating 100 exercises costs less than a single penny!).

2. **Create a Card Manually (Default — No AI / No API Key Needed)**:
   - Open the generator by clicking the brain icon (🧠) in Anki's editor toolbar or pressing **Ctrl+Shift+G**. **Manual Entry** is the first tab.
   - Type your sentence, marking each blank with `___` (three or more underscores) — use it twice for a double-blank card.
   - Enter the correct answer and a comma-separated list of wrong options for each blank.
   - A table lists every option (the correct answer first). Optionally write why each option is right or wrong; leave cells empty for a simpler card.
   - Optional: click **Generate Missing Explanations** to let the AI fill only the empty cells (needs an API key). It never changes text you wrote, and you can edit the results before saving.
   - Click **Create Card** (or **Insert into Card**). No AI call is ever made when you save.

3. **Optional: Generate a Card with AI** (the **AI: Generate Card** and **AI: Suggest Options** tabs):
   - Enter a target sentence you want to practice, or leave it blank to let the AI build one from scratch.
   - Choose the target language, difficulty tier (A1-C2), and the grammar topic (Verb Forms, Nouns, Adjectives, Prepositions, etc.).
   - Click **Generate and Create Card**.
   - The card is parsed and saved instantly to your current active deck!

4. **Practice**:
   - Review your cards. The blank space is replaced by a dropdown menu populated with smart grammatical distractors.
   - Choose your answer and click **Check Answer** to get instant feedback and a detailed grammatical breakdown explaining the syntax rules!
