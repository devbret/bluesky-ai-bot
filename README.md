# Bluesky AI Bot

This program continuously searches the Bluesky network for recent posts matching specific keywords, then collects them and processes the content through a local AI summarization model.

The combined text from relevant posts is analyzed and condensed into a short summary to capture the essence of the discussion around the keyword. Each batch of collected posts is saved to a daily JSONL file in a data directory for record-keeping and later analysis.

Before posting, the generated summary undergoes content moderation to ensure it meets common sense guidelines. If approved, the summary is then posted to the bot’s connected Bluesky account. The program also logs all summaries and any errors encountered in separate log files for traceability.

Built with fault tolerance in mind, it uses threading, retries and timeout safeguards to keep the bot running smoothly in continuous cycles, making Bluesky AI Bot a fully autonomous social summarization and posting system.
