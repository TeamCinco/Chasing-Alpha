Okay, here are example commands to run the `trader.py` script, assuming:

1.  You have all the Python files (`trader.py`, `config.py`, `auth_manager.py`, `api_client.py`, `order_builder.py`, `utils.py`) in the same directory.
2.  You have created a `.env` file in that same directory with your `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, `SCHWAB_CALLBACK_URL`, and optionally `SCHWAB_ACCOUNT_NUMBER` or `SCHWAB_ACCOUNT_HASH`.
3.  You have installed the necessary libraries: `pip install requests python-dotenv`.
4.  You are running these commands from your terminal in the directory where the scripts are located.

**First-Time Setup / Authentication:**

If it's your first time or your tokens have expired and `schwab_tokens.json` doesn't exist or is invalid:

```bash
# This command will trigger the OAuth flow if tokens are needed
python trader.py get_accounts
```

*   The script will print a URL. Open it in your browser.
*   Log in to Schwab and authorize the application.
*   You'll be redirected to your `SCHWAB_CALLBACK_URL`. Copy the **entire URL** from your browser's address bar.
*   Paste this URL back into the terminal when prompted.
*   `schwab_tokens.json` will be created/updated.

**Common Commands:**

**1. Get Account Information:**

*   **List all linked accounts (shows numbers and their hashes):**
    ```bash
    python trader.py get_accounts
    ```
    *Take note of the `hashValue` for the account you want to trade with.*

*   **Get balance and positions for a specific account (using its hash):**
    ```bash
    python trader.py get_balance --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(Replace `YOUR_ENCRYPTED_ACCOUNT_HASH_HERE` with the actual hash)*

*   **Get balance (if `SCHWAB_ACCOUNT_HASH` is in `.env` or only one account linked):**
    ```bash
    python trader.py get_balance
    ```

*   **Get balance (if `SCHWAB_ACCOUNT_NUMBER` is in `.env` and you want to use it for lookup):**
    ```bash
    python trader.py get_balance
    ```

*   **Get balance (specifying account number for lookup via CLI):**
    ```bash
    python trader.py get_balance --account_number YOUR_SCHWAB_ACCOUNT_NUMBER
    ```

**2. Placing Equity Orders:**
   *(Remember to replace `YOUR_ENCRYPTED_ACCOUNT_HASH_HERE` or ensure your `.env` is set up for account selection)*

*   **Buy 10 shares of AAPL at Market price:**
    ```bash
    python trader.py buy --symbol AAPL --quantity 10 --order_type MARKET --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(Without `--account_hash`, it will try to use `.env` settings or interactive selection)*

*   **Sell 5 shares of MSFT with a Limit price of $400.00, Good Till Cancel:**
    ```bash
    python trader.py sell --symbol MSFT --quantity 5 --order_type LIMIT --price 400.00 --duration GOOD_TILL_CANCEL --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Buy 2 shares of GOOG with a Stop order at $150.00:**
    ```bash
    python trader.py buy --symbol GOOG --quantity 2 --order_type STOP --stop_price 150.00 --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Sell 1 share of TSLA with a Stop Limit order (Stop at $180.00, Limit at $179.50):**
    ```bash
    python trader.py sell --symbol TSLA --quantity 1 --order_type STOP_LIMIT --stop_price 180.00 --price 179.50 --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Sell 3 shares of NVDA with a Trailing Stop of $5.00 (value offset from LAST price):**
    ```bash
    python trader.py sell --symbol NVDA --quantity 3 --order_type TRAILING_STOP --trailing_offset 5.00 --trailing_basis LAST --trailing_type VALUE --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Buy 10 shares of AMD with a Trailing Stop of 2.5% (percent offset from MARK price):**
    ```bash
    python trader.py buy --symbol AMD --quantity 10 --order_type TRAILING_STOP --trailing_offset 2.5 --trailing_basis MARK --trailing_type PERCENT --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Place an order and automatically confirm (USE WITH CAUTION!):**
    ```bash
    python trader.py buy --symbol F --quantity 100 --order_type MARKET --account_hash YOUR_HASH -y
    ```

**3. Managing Orders:**

*   **Get a list of recent orders for an account:**
    ```bash
    python trader.py get_orders --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Get details for a specific order:**
    ```bash
    python trader.py get_order --order_id YOUR_ORDER_ID_HERE --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Cancel a specific order:**
    ```bash
    python trader.py cancel_order --order_id YOUR_ORDER_ID_HERE --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(Will prompt for confirmation unless `-y` is used)*

*   **Replace an existing order (e.g., change the limit price of order 123 for AAPL to $175):**
    ```bash
    python trader.py replace_order --order_id 123 --symbol AAPL --quantity 10 --order_type LIMIT --price 175.00 --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(This assumes the original order was for 10 shares of AAPL and you're only changing the price. You need to provide all necessary fields for the *new* order definition.)*

**4. Utility Commands:**

*   **Force re-authentication (deletes `schwab_tokens.json` before running):**
    ```bash
    python trader.py get_accounts --force_reauth
    ```

**Important Reminders:**

*   **Account Hash/Number:** If you don't provide `--account_hash` or `--account_number` on the command line, the script will try to use `SCHWAB_ACCOUNT_HASH` or `SCHWAB_ACCOUNT_NUMBER` from your `.env` file. If neither of those are set and multiple accounts are linked, it will prompt you to choose.
*   **Confirmation:** Most actions that modify orders or place new ones will ask for confirmation unless you use the `-y` or `--yes` flag. **Be very careful with the `-y` flag, especially with real money.**
*   **Error Messages:** Pay attention to any error messages from the script or the API.
*   **Testing:** **ALWAYS test with small, inconsequential amounts or in a paper trading environment if available when dealing with financial APIs.** The Charles Schwab Trader API sandbox was "coming later this year" according to the initial docs, so check its current status.

These commands should cover the main functionalities of the script. Adjust symbols, quantities, prices, and account hashes to your specific needs.Okay, here are example commands to run the `trader.py` script, assuming:

1.  You have all the Python files (`trader.py`, `config.py`, `auth_manager.py`, `api_client.py`, `order_builder.py`, `utils.py`) in the same directory.
2.  You have created a `.env` file in that same directory with your `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, `SCHWAB_CALLBACK_URL`, and optionally `SCHWAB_ACCOUNT_NUMBER` or `SCHWAB_ACCOUNT_HASH`.
3.  You have installed the necessary libraries: `pip install requests python-dotenv`.
4.  You are running these commands from your terminal in the directory where the scripts are located.

**First-Time Setup / Authentication:**

If it's your first time or your tokens have expired and `schwab_tokens.json` doesn't exist or is invalid:

```bash
# This command will trigger the OAuth flow if tokens are needed
python trader.py get_accounts
```

*   The script will print a URL. Open it in your browser.
*   Log in to Schwab and authorize the application.
*   You'll be redirected to your `SCHWAB_CALLBACK_URL`. Copy the **entire URL** from your browser's address bar.
*   Paste this URL back into the terminal when prompted.
*   `schwab_tokens.json` will be created/updated.

**Common Commands:**

**1. Get Account Information:**

*   **List all linked accounts (shows numbers and their hashes):**
    ```bash
    python trader.py get_accounts
    ```
    *Take note of the `hashValue` for the account you want to trade with.*

*   **Get balance and positions for a specific account (using its hash):**
    ```bash
    python trader.py get_balance --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(Replace `YOUR_ENCRYPTED_ACCOUNT_HASH_HERE` with the actual hash)*

*   **Get balance (if `SCHWAB_ACCOUNT_HASH` is in `.env` or only one account linked):**
    ```bash
    python trader.py get_balance
    ```

*   **Get balance (if `SCHWAB_ACCOUNT_NUMBER` is in `.env` and you want to use it for lookup):**
    ```bash
    python trader.py get_balance
    ```

*   **Get balance (specifying account number for lookup via CLI):**
    ```bash
    python trader.py get_balance --account_number YOUR_SCHWAB_ACCOUNT_NUMBER
    ```

**2. Placing Equity Orders:**
   *(Remember to replace `YOUR_ENCRYPTED_ACCOUNT_HASH_HERE` or ensure your `.env` is set up for account selection)*

*   **Buy 10 shares of AAPL at Market price:**
    ```bash
    python trader.py buy --symbol AAPL --quantity 10 --order_type MARKET --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(Without `--account_hash`, it will try to use `.env` settings or interactive selection)*

*   **Sell 5 shares of MSFT with a Limit price of $400.00, Good Till Cancel:**
    ```bash
    python trader.py sell --symbol MSFT --quantity 5 --order_type LIMIT --price 400.00 --duration GOOD_TILL_CANCEL --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Buy 2 shares of GOOG with a Stop order at $150.00:**
    ```bash
    python trader.py buy --symbol GOOG --quantity 2 --order_type STOP --stop_price 150.00 --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Sell 1 share of TSLA with a Stop Limit order (Stop at $180.00, Limit at $179.50):**
    ```bash
    python trader.py sell --symbol TSLA --quantity 1 --order_type STOP_LIMIT --stop_price 180.00 --price 179.50 --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Sell 3 shares of NVDA with a Trailing Stop of $5.00 (value offset from LAST price):**
    ```bash
    python trader.py sell --symbol NVDA --quantity 3 --order_type TRAILING_STOP --trailing_offset 5.00 --trailing_basis LAST --trailing_type VALUE --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Buy 10 shares of AMD with a Trailing Stop of 2.5% (percent offset from MARK price):**
    ```bash
    python trader.py buy --symbol AMD --quantity 10 --order_type TRAILING_STOP --trailing_offset 2.5 --trailing_basis MARK --trailing_type PERCENT --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Place an order and automatically confirm (USE WITH CAUTION!):**
    ```bash
    python trader.py buy --symbol F --quantity 100 --order_type MARKET --account_hash YOUR_HASH -y
    ```

**3. Managing Orders:**

*   **Get a list of recent orders for an account:**
    ```bash
    python trader.py get_orders --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Get details for a specific order:**
    ```bash
    python trader.py get_order --order_id YOUR_ORDER_ID_HERE --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```

*   **Cancel a specific order:**
    ```bash
    python trader.py cancel_order --order_id YOUR_ORDER_ID_HERE --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(Will prompt for confirmation unless `-y` is used)*

*   **Replace an existing order (e.g., change the limit price of order 123 for AAPL to $175):**
    ```bash
    python trader.py replace_order --order_id 123 --symbol AAPL --quantity 10 --order_type LIMIT --price 175.00 --account_hash YOUR_ENCRYPTED_ACCOUNT_HASH_HERE
    ```
    *(This assumes the original order was for 10 shares of AAPL and you're only changing the price. You need to provide all necessary fields for the *new* order definition.)*

**4. Utility Commands:**

*   **Force re-authentication (deletes `schwab_tokens.json` before running):**
    ```bash
    python trader.py get_accounts --force_reauth
    ```

**Important Reminders:**

*   **Account Hash/Number:** If you don't provide `--account_hash` or `--account_number` on the command line, the script will try to use `SCHWAB_ACCOUNT_HASH` or `SCHWAB_ACCOUNT_NUMBER` from your `.env` file. If neither of those are set and multiple accounts are linked, it will prompt you to choose.
*   **Confirmation:** Most actions that modify orders or place new ones will ask for confirmation unless you use the `-y` or `--yes` flag. **Be very careful with the `-y` flag, especially with real money.**
*   **Error Messages:** Pay attention to any error messages from the script or the API.
*   **Testing:** **ALWAYS test with small, inconsequential amounts or in a paper trading environment if available when dealing with financial APIs.** The Charles Schwab Trader API sandbox was "coming later this year" according to the initial docs, so check its current status.

These commands should cover the main functionalities of the script. Adjust symbols, quantities, prices, and account hashes to your specific needs.