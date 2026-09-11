import yfinance as yf 
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import ta  # Technical Analysis library

st.set_page_config(
    page_title = "Advanced Stock Analyzer",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

#Sidebar for user inputs
st.sidebar.header("Stock Selection")
# stock selection
tickerSymbol = st.sidebar.text_input("Enter Stock Symbol", value = "GOOGL").upper()

# Date range selection
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "Start Date",
        value = datetime.now() - timedelta(days = 365*10)
    )

with col2:
    end_date = st.date_input(
        "End Date",
        value = datetime.now()
    )

# Advanced Options
st.sidebar.header("Advanced Options")
show_ma = st.sidebar.checkbox("Show Moving Averages", value = True)
ma_periods = st.sidebar.multiselect(
    "MA Periods",
    options = [10, 20, 50, 100, 200],
    default = [20, 50]
)
show_bollinger = st.sidebar.checkbox("Show Bollinger Bands", value = False)
show_rsi = st.sidebar.checkbox("Show RSI Indicator", value = True)
show_macd = st.sidebar.checkbox("Show MACD Indicator", value = True)
show_volume = st.sidebar.checkbox("Show Volume", value = True)
comparsion_ticker = st.sidebar.text_input("Compare with", value = "")

# Risk and Backtest Options
st.sidebar.header("Risk & Backtest")
show_risk_metrics = st.sidebar.checkbox("Show Risk Metrics", value = True)
risk_free_rate = st.sidebar.number_input(
    "Risk-Free Rate (annual, %)", min_value=0.0, max_value = 20.0, value = 2.0, step = 0.25
) / 100

run_Backtest = st.sidebar.checkbox("Run MA Crossover BAcktest", value = False)
backtest_short_window = st.sidebar.number_input(
    "Backtest Short MA", min_value = 2, max_value = 100, value = 20
)
backtest_long_window = st.sidebar.number_input(
    "Backtest Short MA", min_value = 5, max_value = 300, value = 50
)

# Main Title
st.markdown(f'<h1 class = "main-header">{tickerSymbol}</h1>', unsafe_allow_html = True)

# Fetch data with caching
@st.cache_data(ttl = 3600)
def fetch_stock_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(start = start, end = end)
        return data, stock.info 
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, None 

# Fetch comparison data
@st.cache_data(ttl = 3600)
def fetch_comparison_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(start = start, end = end)
        return data 
    except:
        return None

def compute_risk_metrics(price_series, risk_free_rate = 0.2, trading_days = 252):
    returns = price_series.pct_change().dropna()
    n_years = len(price_series) / trading_days

    cagr = (price_series.iloc[-1] / price_series.iloc[0]) ** (1/n_years) -1 if n_years > 0 else np.nan

    ann_return = returns.mean() * trading_days
    ann_vol = returns.std() * np.sqrt(trading_days)
    sharpe = (ann_return - risk_free_rate) / ann_vol if ann_vol not in (0, np.nan) else np.nan 

    downside_return = returns[returns < 0]
    downside_vol = downside_return.std() * np.sqrt(trading_days)
    sortino = (ann_return - risk_free_rate) / downside_vol if downside_vol not in (0, np.nan) else np.nan 

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    calmar = cagr / abs(max_drawdown) if max_drawdown not in (0, np.nan) else np.nan

    var_95 = returns.quantile(0.05)
    cvar_95 = returns[returns <= var_95].mean()

    return {
        'CAGR': cagr,
        'Annualized Volatility': ann_vol,
        'Sharpe Ratio': sharpe,
        'Sortino Ratio': sortino,
        'Max Drawdown': max_drawdown,
        'Calmar Ratio': calmar,
        'VaR (95%, daily)': var_95,
        'CVaR (95%, daily)': cvar_95,
        'Skewness': returns.skew(),
        'Kurtosis': returns.kurtosis(),
        'drawdown_series': drawdown
    }

# MA Crossover Backtest
def backtest_ma_crossover(price_data, short_window, long_window):
    df = price_data.copy()
    df['Short_MA'] = df['Close'].rolling(window = short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window = long_window).mean()

    df['Signal'] = 0
    valid = df['Short_MA'].notna() & df['Long_MA'].notna()
    df.loc[valid, 'Signal'] = np.where(df.loc[valid, 'Short_MA'] > df.loc[valid, 'Long_MA'], 1, 0)
    df['Position_Change'] = df['Signal'].diff()

    df['Market_Return'] = df['Close'].pct_change()
    df['Strategy_Return'] = df['Market_Return'] * df['Signal'].shift(1)

    df['Cumulative_Market'] = (1 + df['Market_Return'].fillna(0)).cumprod()
    df['Cumulative_Strategy'] = (1 + df['Strategy_Return'].fillna(0)).cumprod()

    trades = df[df['Position_Change'] != 0]
    num_trades = int(len(trades))

    nonzero_strategy_returns = df['Strategy_Return'].dropna()
    nonzero_strategy_returns = nonzero_strategy_returns[nonzero_strategy_returns != 0]
    win_rate = (nonzero_strategy_returns > 0).sum() / len(nonzero_strategy_returns) if len(nonzero_strategy_returns) > 0 else np.nan 

    strat_cumulative = df['Cumulative_Strategy']
    strat_running_max = strat_cumulative.cummax()
    strat_drawdown = (strat_cumulative - strat_running_max) / strat_running_max
    strat_max_dd = strat_drawdown.min()

    total_strategy_return = df['Cumulative_Strategy'].iloc[-1] - 1
    total_market_return = df['Cumulative_Market'].iloc[-1] - 1

    metrics = {
        'num_trades': num_trades,
        'win_rate': win_rate,
        'strategy_max_drawdown': strat_max_dd,
        'total_strategy_return': total_strategy_return,
        'total_market_return': total_market_return
    }
    return df, metrics

# Load data 
data, info = fetch_stock_data(tickerSymbol, start_date, end_date)

if data is not None and not data.empty:
    # Calculate indicators
    # Moving Averages
    for period in ma_periods:
        data[f'MA_{period}'] = data['Close'].rolling(window = period).mean()

    # Bollinger Bands
    if show_bollinger:
        data['MA_20'] = data['Close'].rolling(window = 20).mean()
        data['STD_20'] = data['Close'].rolling(window = 20).std()
        data['Upper_Band'] = data['MA_20'] + (data['STD_20'] * 2)
        data['Lower_Band'] = data['MA_20'] - (data['STD_20'] * 2)

    # RSI
    if show_rsi:
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window = 14).rsi()

    # MACD
    if show_macd:
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        data['MACD_diff'] = macd.macd_diff()

    # Fetch comparison data
    comp_data = None
    if comparsion_ticker:
        comp_data = fetch_comparison_data(comparsion_ticker, start_date, end_date)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Company",
            info.get('shortName', tickerSymbol)[:30] + '...'
        )
    with col2:
        current_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[-2]
        change = ((current_price - prev_price) / prev_price) * 100
        st.metric(
            "Current Price",
            f"${current_price:.2f}",
            f"{change:.2f}"
        )
    with col3: 
        st.metric(
            "Volume",
            f"{data['Volume'].iloc[-1]:,.0f}"
        )
    with col4: 
        st.metric(
            "Market Cap",
            f"${info.get('marketCap', 0) / 1e9:.2f}B"
        )

    # Create main pie chart
    # Determine number of rows needed
    n_rows = 2 # price + volume 
    if show_rsi:
        n_rows += 1
    if show_macd:
        n_rows += 1 

    # Create subplot titles
    subtitles = [f'{tickerSymbol} Price']
    if show_volume:
        subtitles.append("Volume")
    if show_rsi:
        subtitles.append("RSI")
    if show_macd:
        subtitles.append("MACD")

    # Create subplot with appropriate rows
    fig = make_subplots(
        rows = n_rows,
        cols = 1,
        shared_xaxes = True, 
        vertical_spacing = 0.08,
        row_heights=[0.5, 0.15, 0.175, 0.175][:n_rows],  # price gets 50%, others smaller
        subplot_titles = subtitles
    )

    row_counter = 1

    # Price Chart
    fig.add_trace(
        go.Scatter(
            x = data.index,
            y = data['Close'],
            mode = 'lines',
            name = 'Price',
            line = dict(color = '#1f77b4', width = 2)
        ),
        row = row_counter, col = 1
    )

    # Moving averages
    if show_ma:
        colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        for i, period in enumerate(ma_periods):
            if f'MA_{period}' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x = data.index,
                        y = data[f'MA_{period}'],
                        mode = 'lines',
                        name = f'MA {period}',
                        line = dict(color = colors[i % len(colors)], width = 1.5)
                    ),
                    row = row_counter, col = 1
                )

    # Bollinger Bands
    if show_bollinger:
        fig.add_trace(
            go.Scatter(
                x = data.index,
                y = data['Upper_Band'],
                mode = 'lines',
                name = 'Upper Band',
                line = dict(color = 'rgba(255, 0, 0, 0.3)', dash = 'dash')
            ),
            row = row_counter, col = 1
        )
        fig.add_trace(
            go.Scatter(
                x = data.index,
                y = data['Lower_Band'],
                mode = 'lines',
                name = 'Lower Band',
                line = dict(color = 'rgba(255, 0, 0, 0.3)', dash = 'dash')
            ),
            row = row_counter, col = 1
        )

    # Comparison ticker
    if comp_data is not None and not comp_data.empty:
        # Normalize to percentage change for comparison
        norm_data = data['Close'] / data['Close'].iloc[0] * 100
        norm_comp = comp_data['Close'] / comp_data['Close'].iloc[0] * 100
        fig.add_trace(
            go.Scatter(
                x = comp_data.index,
                y = norm_comp,
                mode = 'lines',
                name = f'{comparsion_ticker} (%)',
                line = dict(color = 'green', width = 2, dash = 'dot')
            ),
            row = row_counter, col = 1
        )

    row_counter += 1

    # Volume (row 2)
    if show_volume:
        # Build color list aligned with data index
        vol_colors = []
        for i in range(len(data)):
            if i == 0:
                vol_colors.append('green')
            else:
                if data['Close'].iloc[i] >= data['Close'].iloc[i-1]:
                    vol_colors.append('green')
                else:
                    vol_colors.append('red')

        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['Volume'],
                name='Volume',
                marker=dict(color=vol_colors, line=dict(width=0)),
                opacity=1.0
            ),
            row=row_counter, col=1
        )
        row_counter += 1

    # RSI
    if show_rsi:
        fig.add_trace(
            go.Scatter(
                x = data.index,
                y = data['RSI'],
                mode = 'lines',
                name = 'RSI',
                line = dict(color = 'purple', width = 2)
            ),
            row = row_counter, col = 1
        )
        fig.add_hline(y = 70, line_dash = 'dash', line_color = 'red', row = row_counter, col = 1)
        fig.add_hline(y = 30, line_dash = 'dash', line_color = 'green', row = row_counter, col = 1)
        fig.add_hrect(y0 = 70, y1 = 100, line_dash = 'dash', line_color = 'red', opacity = 0.1,  row = row_counter, col = 1)
        fig.add_hrect(y0 = 0, y1 = 30, line_dash = 'dash', line_color = 'green', opacity = 0.1,  row = row_counter, col = 1)

        row_counter += 1

    # MACD
    if show_macd:
        fig.add_trace(
            go.Scatter(
                x = data.index,
                y = data['MACD'],
                mode = 'lines',
                name = 'MACD',
                line = dict(color = 'blue', width = 2)
            ),
            row = row_counter, col = 1
        )
        fig.add_trace(
            go.Scatter(
                x = data.index,
                y = data['MACD_signal'],
                mode = 'lines',
                name = 'signal',
                line = dict(color = 'red', width = 2)
            ),
            row = row_counter, col = 1
        )
        # Add MACD histogram
        colors = ['green' if val >= 0 else 'red' for val in data['MACD_diff']]
        fig.add_trace(
            go.Bar(
                x = data.index,
                y = data['MACD_diff'],
                name = 'Histogram',
                marker_color = colors,
                opacity = 0.5
            ),
            row = row_counter, col = 1
        )
        row_counter += 1

    # Update layout 
    fig.update_layout(
        height = 200 + (n_rows * 200),
        showlegend = True, 
        hovermode = 'x unified',
        template = 'plotly_white',
        legend = dict(
            orientation = 'h',
            yanchor = 'bottom',
            y = 1.02,
            xanchor = 'right',
            x = 1
        )
    )

    fig.update_xaxes(title_text = 'Date', row = n_rows, col = 1)
    fig.update_yaxes(title_text = 'Price ($)', row = n_rows, col = 1)
    if show_volume:
        fig.update_yaxes(title_text = 'Volume', row = 2, col = 1)

    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    # Additional statistics
    st.subheader("Key Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "52 Week High",
            f"${info.get('fiftyTwoWeekHigh', 0):.2f}"
        )
        st.metric(
            "52 Week Low",
            f"${info.get('fiftyTwoWeekLow', 0):.2f}"
        )

    with col2:
        st.metric(
            "P/E Ratio",
            f"{info.get('trailingPE', 0):.2f}"
        )
        st.metric(
            "EPS",
            f"${info.get('trailingEps', 0):.2f}"
        )

    with col3:
        st.metric(
            "Dividend Yield",
            f"{info.get('dividendYield', 0) * 100:.2f}%"
        )
        st.metric(
            "Beta",
            f"{info.get('beta', 0):.2f}"
        )

    with col4:
        # Calculate returns
        returns = data['Close'].pct_change()
        st.metric(
            "Volatility (30d)",
            f"{returns.tail(30).std() * 100:.2f}%"
        )
        st.metric(
            "Total Return",
            f"{((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100:.2f}%"
        )

    
    st.divider()
    # Risk & Performance Metrics 
    if show_risk_metrics:
        st.subheader("Risk & Performance Metrics")
        risk = compute_risk_metrics(data['Close'], risk_free_rate = risk_free_rate)

        rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns(5)
        with rcol1:
            st.metric("CAGR", f"{risk["CAGR"] * 100:.2f}")
            st.metric("Ann. Volatility", f"{risk["Annualized Volatility"] * 100:.2f}")
        with rcol2:
            st.metric("Sharpe Ratio", f"{risk["Sharpe Ratio"]:.2f}")
            st.metric("Sortino Ratio", f"{risk["Sortino Ratio"]:.2f}")
        with rcol3:
            st.metric("Max Drawdown", f"{risk["Max Drawdown"] * 100:.2f}")
            st.metric("Calmar Ratio", f"{risk["Calmar Ratio"]:.2f}")
        with rcol4:
            st.metric("VaR (95%, daily)", f"{risk["VaR (95%, daily)"] * 100:.2f}")
            st.metric("CVaR (95%, daily)", f"{risk["CVaR (95%, daily)"] * 100:.2f}")
        with rcol5:
            st.metric("Skewness", f"{risk["Skewness"]:.2f}")
            st.metric("Kurtosis", f"{risk["Kurtosis"]:.2f}")

        dd_fig = go.Figure()
        dd_fig.add_trace(
            go.Scatter(
                x = risk['drawdown_series'].index,
                y = risk['drawdown_series'] * 100 ,
                mode = 'lines',
                name = 'Drawdown',
                fill = 'tozeroy',
                line = dict(color = '#d62728', width = 1.5)
            )
        )
        dd_fig.update_layout(
            title = 'Drawdown Over Time (%)',
            template = 'plotly_white',
            height = 300,
            yaxis_title = 'Drawdown (%)'
        )
        st.plotly_chart(dd_fig, use_container_width=True)

    # MA Crossover Backtest 
    if run_Backtest:
        st.subheader("MA Crossover Backtest")
        if backtest_short_window >= backtest_long_window:
            st.warning("Short MA window should be smaller than the Long MA window for a meaningful crossover strategy.")
        else:
            bt_df, bt_metrics = backtest_ma_crossover(data, backtest_short_window, backtest_long_window)

            bcol1, bcol2, bcol3, bcol4 = st.columns(4)
            with bcol1:
                st.metric("Strategy Return", f"{bt_metrics['total_strategy_return'] * 100:.2f}%")
            with bcol2:
                st.metric("Buy & Hold Return", f"{bt_metrics['total_market_return'] * 100:.2f}%")
            with bcol3:
                st.metric("Number of Trades", f"{bt_metrics['num_trades']}")
            with bcol4:
                st.metric("Win Rate", f"{bt_metrics['win_rate'] * 100:.2f}%")

            st.metric("Strategy Max Drawdown", f"{bt_metrics['strategy_max_drawdown'] * 100:.2f}%")

            bt_fig = go.Figure()
            bt_fig.add_trace(
                go.Scatter(
                    x = bt_df.index,
                    y = (bt_df['Cumulative_Strategy'] - 1) * 100,
                    mode = 'lines',
                    name = f'MA({backtest_short_window}/{backtest_long_window}) Strategy',
                    line = dict(color = '#2ca02c', width = 2)
            )
            )

            bt_fig.add_trace(
                go.Scatter(
                    x = bt_df.index,
                    y = (bt_df['Cumulative_Market'] - 1) * 100,
                    mode = 'lines',
                    name = 'Buy & Hold',
                    line = dict(color = '#1f77b4', width = 2, dash = 'dash')
                )
            )
            bt_fig.update_layout(
                title = "Cumulative Return: Strategy vs Buy & Hold",
                template = 'plotly_white',
                height = 400,
                yaxis_title = 'Cumulative Return (%)',
                hovermode = 'x unified',
                legend = dict(orientation = 'h', yanchor = 'bottom', y = 1.02, xanchor = 'right', x = 1)
            )
            st.plotly_chart(bt_fig, use_container_width = True)

            st.caption(
                "Backtest assumes the strategy holds the stock while Short MA > Long MA and is in cash otherwise, "
                "with no transaction costs or slippage. This is illustrative, not investment advice."
            )

    st.divider()
    # Download data option
    st.subheader("📥 Download Data")
    csv = data.to_csv()
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"{tickerSymbol}_data.csv",
        mime="text/csv"
    )

else:
    st.error(f"Could not fetch data for {tickerSymbol}. Please check the symbol and try again.")