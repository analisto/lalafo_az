import os
import sys
import warnings
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

# ── paths ──────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_HERE, "..")
CHARTS_DIR = os.path.join(ROOT, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── load & deduplicate ─────────────────────────────────────────────────────────
tr_raw = pd.read_csv(os.path.join(ROOT, "data", "transport.csv"))
ho_raw = pd.read_csv(os.path.join(ROOT, "data", "home.csv"))

tr = tr_raw.drop_duplicates(subset="id", keep="first").copy()
ho = ho_raw.drop_duplicates(subset="id", keep="first").copy()

for df in [tr, ho]:
    df["created_dt"] = pd.to_datetime(df["created_time"], unit="s")
    df["year"] = df["created_dt"].dt.year
    df["ym"] = df["created_dt"].dt.strftime("%Y-%m")

# ── style ──────────────────────────────────────────────────────────────────────
BLUE   = "#2563EB"
TEAL   = "#0891B2"
AMBER  = "#D97706"
GREEN  = "#16A34A"
SLATE  = "#475569"
LGRAY  = "#F1F5F9"

def base_style(ax, title, xlabel="", ylabel=""):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12, color="#1E293B")
    ax.set_xlabel(xlabel, fontsize=10, color=SLATE)
    ax.set_ylabel(ylabel, fontsize=10, color=SLATE)
    ax.tick_params(colors=SLATE, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.set_facecolor(LGRAY)
    ax.yaxis.grid(True, color="white", linewidth=1.2)
    ax.set_axisbelow(True)


# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Monthly New Listing Volume  (Jan 2025 → Jan 2026)
# ══════════════════════════════════════════════════════════════════════════════
def chart_monthly_volume():
    months = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01"]

    tr_vol = tr[tr["ym"].isin(months)].groupby("ym").size().reindex(months, fill_value=0)
    ho_vol = ho[ho["ym"].isin(months)].groupby("ym").size().reindex(months, fill_value=0)

    labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec'25", "Jan'26"
    ]
    x = range(len(months))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(x, tr_vol.values, marker="o", color=BLUE,  linewidth=2.2,
            markersize=6, label="Transport")
    ax.plot(x, ho_vol.values, marker="s", color=AMBER, linewidth=2.2,
            markersize=6, label="Home & Garden")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    base_style(ax,
               "Monthly New Listings — Transport vs Home & Garden (Jan 2025 – Jan 2026)",
               ylabel="Number of New Listings")
    ax.legend(fontsize=10, frameon=False)

    # annotate last point
    for series, color in [(tr_vol, BLUE), (ho_vol, AMBER)]:
        ax.annotate(f"{series.iloc[-1]:,}",
                    xy=(len(months)-1, series.iloc[-1]),
                    xytext=(8, 0), textcoords="offset points",
                    color=color, fontweight="bold", fontsize=9, va="center")

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "01_monthly_volume.png"), dpi=150)
    plt.close()
    print("✓  01_monthly_volume.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — Top Cities by Listing Count
# ══════════════════════════════════════════════════════════════════════════════
def chart_city_distribution():
    top_cities_tr = tr["city"].value_counts().head(8)
    top_cities_ho = ho["city"].value_counts().head(8)

    all_cities = list(dict.fromkeys(
        list(top_cities_tr.index) + list(top_cities_ho.index)
    ))[:10]

    tr_vals = [tr["city"].value_counts().get(c, 0) for c in all_cities]
    ho_vals = [ho["city"].value_counts().get(c, 0) for c in all_cities]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, vals, title, color in [
        (axes[0], tr_vals, "Transport — Listings by City", BLUE),
        (axes[1], ho_vals, "Home & Garden — Listings by City", AMBER),
    ]:
        bars = ax.barh(all_cities[::-1], vals[::-1], color=color, height=0.6)
        base_style(ax, title, xlabel="Number of Listings")
        for bar, val in zip(bars, vals[::-1]):
            ax.text(bar.get_width() + max(vals)*0.01, bar.get_y() + bar.get_height()/2,
                    f"{val:,}", va="center", fontsize=8.5, color=SLATE)
        ax.set_xlim(0, max(vals) * 1.18)

    fig.tight_layout(pad=3)
    fig.savefig(os.path.join(CHARTS_DIR, "02_city_distribution.png"), dpi=150)
    plt.close()
    print("✓  02_city_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 3 — Price Bracket Distribution
# ══════════════════════════════════════════════════════════════════════════════
def chart_price_distribution():
    def bucketize(df, bins, labels):
        d = df[(df["currency"] == "AZN") & df["price"].notna()].copy()
        p99 = d["price"].quantile(0.99)
        d = d[d["price"] <= p99]
        d["bracket"] = pd.cut(d["price"], bins=bins, labels=labels)
        return d["bracket"].value_counts().reindex(labels, fill_value=0)

    tr_b = bucketize(tr,
                     [0, 100, 500, 1_000, 5_000, 10_000, 50_000, float("inf")],
                     ["0–100", "101–500", "501–1K", "1K–5K", "5K–10K", "10K–50K", "50K+"])
    ho_b = bucketize(ho,
                     [0, 50, 100, 200, 500, 1_000, 5_000, float("inf")],
                     ["0–50", "51–100", "101–200", "201–500", "501–1K", "1K–5K", "5K+"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, data, title, color in [
        (axes[0], tr_b, "Transport — Price Bracket Distribution (AZN)", BLUE),
        (axes[1], ho_b, "Home & Garden — Price Bracket Distribution (AZN)", AMBER),
    ]:
        bars = ax.bar(data.index, data.values, color=color, width=0.6)
        base_style(ax, title, xlabel="Price Range (AZN)", ylabel="Number of Listings")
        ax.set_xticklabels(data.index, rotation=30, ha="right", fontsize=9)
        total = data.sum()
        for bar, val in zip(bars, data.values):
            pct = val / total * 100
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + total*0.005,
                    f"{pct:.0f}%", ha="center", fontsize=8, color=SLATE)

    fig.tight_layout(pad=3)
    fig.savefig(os.path.join(CHARTS_DIR, "03_price_distribution.png"), dpi=150)
    plt.close()
    print("✓  03_price_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 4 — Seller Concentration
# ══════════════════════════════════════════════════════════════════════════════
def chart_seller_concentration():
    def seg_counts(df):
        vc = df["user_id"].value_counts()
        return {
            "1 listing\n(one-off)":     int((vc == 1).sum()),
            "2–5 listings\n(occasional)": int(((vc >= 2) & (vc <= 5)).sum()),
            "6–20 listings\n(active)":  int(((vc >= 6) & (vc <= 20)).sum()),
            "21–100 listings\n(power)": int(((vc >= 21) & (vc <= 100)).sum()),
            "100+ listings\n(dealer)":  int((vc > 100).sum()),
        }

    tr_seg = seg_counts(tr)
    ho_seg = seg_counts(ho)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, seg, title, color in [
        (axes[0], tr_seg, "Transport — Seller Segments by Activity Level", BLUE),
        (axes[1], ho_seg, "Home & Garden — Seller Segments by Activity Level", AMBER),
    ]:
        labels = list(seg.keys())
        vals = list(seg.values())
        bars = ax.bar(labels, vals, color=color, width=0.55)
        base_style(ax, title, ylabel="Number of Sellers")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*0.01,
                    f"{val:,}", ha="center", fontsize=9, fontweight="bold", color=SLATE)
        ax.set_xticklabels(labels, fontsize=8.5)

    fig.tight_layout(pad=3)
    fig.savefig(os.path.join(CHARTS_DIR, "04_seller_segments.png"), dpi=150)
    plt.close()
    print("✓  04_seller_segments.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 5 — Inventory Share: Top Sellers vs the Rest
# ══════════════════════════════════════════════════════════════════════════════
def chart_inventory_share():
    def top_share(df, tops):
        vc = df["user_id"].value_counts()
        total = len(df)
        return {f"Top {t}": vc.head(t).sum() / total * 100 for t in tops}

    tr_share = top_share(tr, [1, 5, 10, 25, 50])
    ho_share = top_share(ho, [1, 5, 10, 25, 50])

    tiers = list(tr_share.keys())
    x = range(len(tiers))
    w = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    b1 = ax.bar([i - w/2 for i in x], list(tr_share.values()), width=w,
                color=BLUE, label="Transport")
    b2 = ax.bar([i + w/2 for i in x], list(ho_share.values()), width=w,
                color=AMBER, label="Home & Garden")

    base_style(ax, "Inventory Concentration: Share of Listings Held by Top Sellers",
               ylabel="% of Total Active Listings")
    ax.set_xticks(list(x))
    ax.set_xticklabels(tiers, fontsize=10)
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.legend(fontsize=10, frameon=False)

    for bar in list(b1) + list(b2):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{bar.get_height():.1f}%", ha="center", fontsize=8.5,
                fontweight="bold", color=SLATE)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "05_inventory_concentration.png"), dpi=150)
    plt.close()
    print("✓  05_inventory_concentration.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 6 — Median Asking Price Trend (2022–2025)
# ══════════════════════════════════════════════════════════════════════════════
def chart_price_trend():
    def yearly_median(df):
        d = df[(df["currency"] == "AZN") & df["price"].notna() & df["year"].between(2022, 2025)].copy()
        p99 = d["price"].quantile(0.99)
        d = d[d["price"] <= p99]
        return d.groupby("year")["price"].median()

    tr_trend = yearly_median(tr)
    ho_trend = yearly_median(ho)
    years = [2022, 2023, 2024, 2025]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(years, [tr_trend.get(y, None) for y in years],
            marker="o", color=BLUE, linewidth=2.2, markersize=8, label="Transport")
    ax.plot(years, [ho_trend.get(y, None) for y in years],
            marker="s", color=AMBER, linewidth=2.2, markersize=8, label="Home & Garden")

    base_style(ax, "Median Asking Price Trend by Year (AZN)",
               ylabel="Median Price (AZN)")
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=10)
    ax.legend(fontsize=10, frameon=False)

    for series, color in [(tr_trend, BLUE), (ho_trend, AMBER)]:
        for yr in years:
            if yr in series.index:
                val = series[yr]
                ax.annotate(f"{val:.0f} AZN",
                            xy=(yr, val), xytext=(0, 10),
                            textcoords="offset points",
                            ha="center", fontsize=9, color=color, fontweight="bold")

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "06_price_trend.png"), dpi=150)
    plt.close()
    print("✓  06_price_trend.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 7 — VIP vs Regular: Price and Photo Quality
# ══════════════════════════════════════════════════════════════════════════════
def chart_vip_comparison():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: Transport — VIP vs regular median price
    tr_azn = tr[(tr["currency"] == "AZN") & tr["price"].notna()].copy()
    p99 = tr_azn["price"].quantile(0.99)
    tr_azn = tr_azn[tr_azn["price"] <= p99]
    tr_vip_price = tr_azn.groupby("is_vip")["price"].median()

    ax = axes[0]
    labels = ["Regular Listings", "VIP Listings"]
    vals = [tr_vip_price.get(False, 0), tr_vip_price.get(True, 0)]
    colors = [SLATE, BLUE]
    bars = ax.bar(labels, vals, color=colors, width=0.5)
    base_style(ax, "Transport — Median Price: VIP vs Regular (AZN)",
               ylabel="Median Asking Price (AZN)")
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f"{val:.0f} AZN", ha="center", fontsize=11,
                fontweight="bold", color=bar.get_facecolor())

    # Right: Home — VIP vs regular avg images
    ho_img = ho.groupby("is_vip")["images_count"].mean()
    ax = axes[1]
    labels2 = ["Regular Listings", "VIP Listings"]
    vals2 = [ho_img.get(False, 0), ho_img.get(True, 0)]
    colors2 = [SLATE, AMBER]
    bars2 = ax.bar(labels2, vals2, color=colors2, width=0.5)
    base_style(ax, "Home & Garden — Avg Photos: VIP vs Regular",
               ylabel="Average Photos per Listing")
    for bar, val in zip(bars2, vals2):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{val:.1f} photos", ha="center", fontsize=11,
                fontweight="bold", color=bar.get_facecolor())

    fig.tight_layout(pad=3)
    fig.savefig(os.path.join(CHARTS_DIR, "07_vip_comparison.png"), dpi=150)
    plt.close()
    print("✓  07_vip_comparison.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 8 — Listing Quality: Images per Listing
# ══════════════════════════════════════════════════════════════════════════════
def chart_listing_quality():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for ax, df, title, color in [
        (axes[0], tr, "Transport — Photo Count Distribution", BLUE),
        (axes[1], ho, "Home & Garden — Photo Count Distribution", AMBER),
    ]:
        vc = df["images_count"].value_counts().sort_index()
        ax.bar(vc.index, vc.values, color=color, width=0.75)
        base_style(ax, title,
                   xlabel="Number of Photos per Listing",
                   ylabel="Number of Listings")
        ax.set_xticks(range(0, 11))
        total = vc.sum()
        zero_pct = vc.get(0, 0) / total * 100
        max10_pct = vc.get(10, 0) / total * 100
        ax.text(0.97, 0.95,
                f"No photo: {zero_pct:.1f}%\n10 photos: {max10_pct:.1f}%",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=9, color=SLATE,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#CBD5E1"))

    fig.tight_layout(pad=3)
    fig.savefig(os.path.join(CHARTS_DIR, "08_listing_quality.png"), dpi=150)
    plt.close()
    print("✓  08_listing_quality.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 9 — Year-on-Year Listing Volume Growth (2020–2025)
# ══════════════════════════════════════════════════════════════════════════════
def chart_yoy_growth():
    years = list(range(2020, 2026))
    tr_yoy = tr[tr["year"].isin(years)].groupby("year").size().reindex(years, fill_value=0)
    ho_yoy = ho[ho["year"].isin(years)].groupby("year").size().reindex(years, fill_value=0)

    x = range(len(years))
    w = 0.35

    fig, ax = plt.subplots(figsize=(11, 5))
    b1 = ax.bar([i - w/2 for i in x], tr_yoy.values, width=w,
                color=BLUE, label="Transport")
    b2 = ax.bar([i + w/2 for i in x], ho_yoy.values, width=w,
                color=AMBER, label="Home & Garden")

    base_style(ax, "Annual Listing Volume Growth (2020–2025)",
               ylabel="Total Listings Created")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(y) for y in years], fontsize=10)
    ax.legend(fontsize=10, frameon=False)

    for bar in list(b1) + list(b2):
        if bar.get_height() > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                    f"{bar.get_height():,}", ha="center", fontsize=8.5,
                    fontweight="bold", color=SLATE)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "09_yoy_growth.png"), dpi=150)
    plt.close()
    print("✓  09_yoy_growth.png")


# ══════════════════════════════════════════════════════════════════════════════
# run all
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating charts...\n")
    chart_monthly_volume()
    chart_city_distribution()
    chart_price_distribution()
    chart_seller_concentration()
    chart_inventory_share()
    chart_price_trend()
    chart_vip_comparison()
    chart_listing_quality()
    chart_yoy_growth()
    print(f"\nAll charts saved to: {os.path.abspath(CHARTS_DIR)}")
