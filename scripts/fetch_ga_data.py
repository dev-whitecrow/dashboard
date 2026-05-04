import os
import json
from datetime import datetime
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    FilterExpressionList,
    Metric,
    RunReportRequest,
)

# acts29-detail.html & acts29-detail-promo.html 페이지 경로 (pagePath 필터용) - thankyou 페이지 포함되도록 .html 제거
TARGET_PAGE = "/groute-contact/acts29-detail"
def make_page_filter():
    """pagePath 필터 생성"""
    return FilterExpression(
        filter=Filter(
            field_name="pagePath",
            string_filter=Filter.StringFilter(
                value=TARGET_PAGE,
                match_type=Filter.StringFilter.MatchType.CONTAINS,
            ),
        )
    )


def make_page_and_event_filter(event_names):
    """pagePath + eventName 복합 필터 생성"""
    return FilterExpression(
        and_group=FilterExpressionList(
            expressions=[
                make_page_filter(),
                FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        in_list_filter=Filter.InListFilter(values=event_names),
                    )
                ),
            ]
        )
    )


def fetch_ga4_data():
    property_id = os.environ.get("GA_PROPERTY_ID")
    if not property_id:
        raise RuntimeError("GA_PROPERTY_ID environment variable not found.")

    client = BetaAnalyticsDataClient()
    date_range = [DateRange(start_date="14daysAgo", end_date="today")]
    target_events = ["detail_page_view", "scroll_depth", "time_on_page", "cta_click", "generate_lead"]

    # 결과 데이터 초기화
    data = {
        "last_updated": datetime.now().isoformat(),
        "ab_available": False,
        "totals": {
            "views": 0,
            "scroll_25": 0, "scroll_50": 0, "scroll_75": 0, "scroll_100": 0,
            "clicks": 0,
            "leads": 0,
            "time_events": 0,
        },
        "ab_test": {
            "A": {
                "views": 0,
                "scroll_25": 0, "scroll_50": 0, "scroll_75": 0, "scroll_100": 0,
                "clicks": 0,
                "leads": 0,
                "time_events": 0,
            },
            "B": {
                "views": 0,
                "scroll_25": 0, "scroll_50": 0, "scroll_75": 0, "scroll_100": 0,
                "clicks": 0,
                "leads": 0,
                "time_events": 0,
            },
        },
        "channels": [],
    }

    # ── 1. A/B 그룹별 이벤트 데이터 시도 ──
    try:
        request_ab = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="customEvent:ab_group"),
            ],
            metrics=[Metric(name="totalUsers")],
            date_ranges=date_range,
            dimension_filter=make_page_and_event_filter(target_events),
        )
        response_ab = client.run_report(request_ab)
        print("✓ A/B group query succeeded.")

        for row in response_ab.rows:
            event_name = row.dimension_values[0].value
            ab_group = row.dimension_values[1].value
            count = int(row.metric_values[0].value)

            if ab_group not in ("A", "B"):
                continue
            if event_name == "detail_page_view":
                data["ab_test"][ab_group]["views"] += count
            elif event_name == "cta_click":
                data["ab_test"][ab_group]["clicks"] += count
            elif event_name == "generate_lead":
                data["ab_test"][ab_group]["leads"] += count
            elif event_name == "time_on_page":
                data["ab_test"][ab_group]["time_events"] += count

    except Exception as e:
        print(f"⚠ A/B group dimension not available yet: {e}")
        print("  → Fetching totals without A/B split.")

    # A/B 데이터 실제 존재 여부 판단
    ab_a = data["ab_test"]["A"]
    ab_b = data["ab_test"]["B"]
    data["ab_available"] = (ab_a["views"] + ab_b["views"]) > 0
    print(f"  A/B available: {data['ab_available']} (A views: {ab_a['views']}, B views: {ab_b['views']})")

    # ── 2. 전체 이벤트 합산 (A/B 무관) ──
    request_totals = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="totalUsers")],
        date_ranges=date_range,
        dimension_filter=make_page_and_event_filter(target_events),
    )
    response_totals = client.run_report(request_totals)

    for row in response_totals.rows:
        event_name = row.dimension_values[0].value
        count = int(row.metric_values[0].value)

        if event_name == "detail_page_view":
            data["totals"]["views"] += count
        elif event_name == "cta_click":
            data["totals"]["clicks"] += count
        elif event_name == "generate_lead":
            data["totals"]["leads"] += count
        elif event_name == "time_on_page":
            data["totals"]["time_events"] += count
        elif event_name == "scroll_depth":
            # scroll_depth 총 이벤트 수 (심도별 분류는 아래에서)
            pass

    print(f"  Total views: {data['totals']['views']}, clicks: {data['totals']['clicks']}")

    # ── 3. 스크롤 심도 데이터 ──
    scroll_event_filter = FilterExpression(
        and_group=FilterExpressionList(
            expressions=[
                make_page_filter(),
                FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(
                            value="scroll_depth",
                            match_type=Filter.StringFilter.MatchType.EXACT,
                        ),
                    )
                ),
            ]
        )
    )

    # 3a. scroll_percent 커스텀 차원으로 심도별 분류 시도
    try:
        request_scroll_detail = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="customEvent:scroll_percent")],
            metrics=[Metric(name="totalUsers")],
            date_ranges=date_range,
            dimension_filter=scroll_event_filter,
        )
        response_scroll = client.run_report(request_scroll_detail)

        for row in response_scroll.rows:
            scroll_pct = row.dimension_values[0].value  # "25", "50", "75", "100"
            count = int(row.metric_values[0].value)
            key = f"scroll_{scroll_pct}"
            if key in data["totals"]:
                data["totals"][key] += count

        print("✓ Scroll depth detail fetched successfully.")

    except Exception as e:
        print(f"⚠ scroll_percent dimension not available: {e}")
        # fallback: scroll_depth 총 이벤트 수만 기록
        request_scroll_total = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="totalUsers")],
            date_ranges=date_range,
            dimension_filter=scroll_event_filter,
        )
        response_scroll_total = client.run_report(request_scroll_total)
        for row in response_scroll_total.rows:
            total_scroll = int(row.metric_values[0].value)
            # 비율 추정 (실제 데이터 없을 때)
            data["totals"]["scroll_25"] = total_scroll
            data["totals"]["scroll_50"] = int(total_scroll * 0.75)
            data["totals"]["scroll_75"] = int(total_scroll * 0.50)
            data["totals"]["scroll_100"] = int(total_scroll * 0.25)
        print("  → Used estimated scroll ratios as fallback.")

    # ── 4. 평균 세션 체류 시간 ──
    request_duration = RunReportRequest(
        property=f"properties/{property_id}",
        metrics=[Metric(name="averageSessionDuration")],
        date_ranges=date_range,
        dimension_filter=make_page_filter(),
    )
    response_duration = client.run_report(request_duration)

    if response_duration.rows:
        avg_sec = float(response_duration.rows[0].metric_values[0].value)
        data["totals"]["avg_session_duration_sec"] = round(avg_sec)
        print(f"✓ Avg session duration: {round(avg_sec)}s")

    # ── 5. 유입 채널 ──
    request_channels = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[
            Metric(name="totalUsers"),
            Metric(name="screenPageViews"),
        ],
        date_ranges=date_range,
        dimension_filter=make_page_filter(),
    )
    response_channels = client.run_report(request_channels)

    for row in response_channels.rows:
        source_medium = row.dimension_values[0].value
        users = int(row.metric_values[0].value)
        data["channels"].append({"source": source_medium, "users": users})

    print(f"✓ Channels: {len(data['channels'])} sources found.")

    return data


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    report_data = fetch_ga4_data()

    with open("data/ga_data.json", "w") as f:
        json.dump(report_data, f, indent=4)
    print("Data successfully exported to data/ga_data.json")
