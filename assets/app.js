document.addEventListener('DOMContentLoaded', async () => {
    // 1. Fetch Data
    let dashboardData;
    try {
        const response = await fetch('data/ga_data.json');
        if (!response.ok) throw new Error('Data file not found');
        dashboardData = await response.json();
    } catch (error) {
        console.warn('GA data not available yet.', error);
        document.getElementById('last-updated').textContent = 'Last Updated: 데이터 없음';
        document.getElementById('total-views').textContent = '-';
        document.getElementById('total-clicks').textContent = '-';
        document.getElementById('overall-conversion').textContent = '-';
        const avgTimeEl = document.getElementById('avg-time');
        if (avgTimeEl) avgTimeEl.textContent = '-';
        return;
    }

    // 2. Update Header & Summary Metrics
    const lastUpdatedDate = new Date(dashboardData.last_updated);
    document.getElementById('last-updated').textContent = `Last Updated: ${lastUpdatedDate.toLocaleString()}`;

    // totals 데이터 사용 (A/B 무관 합산)
    const totals = dashboardData.totals || {};
    const totalViews = totals.views || 0;
    const totalClicks = totals.clicks || 0;
    const convRate = totalViews > 0 ? ((totalClicks / totalViews) * 100).toFixed(1) : '0';

    document.getElementById('total-views').textContent = totalViews.toLocaleString();
    document.getElementById('total-clicks').textContent = totalClicks.toLocaleString();
    document.getElementById('overall-conversion').textContent = `${convRate}%`;

    // Average Time on Page
    const avgTimeEl = document.getElementById('avg-time');
    if (avgTimeEl) {
        const avgSec = totals.avg_session_duration_sec || 0;
        if (avgSec > 0) {
            const mins = Math.floor(avgSec / 60);
            const secs = avgSec % 60;
            avgTimeEl.textContent = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
        } else {
            avgTimeEl.textContent = '-';
        }
    }

    // 3. Render Charts
    const abAvailable = dashboardData.ab_available === true;

    if (abAvailable) {
        // A/B 데이터가 있으면 A/B 비교 퍼널
        const groupA = dashboardData.ab_test.A;
        const groupB = dashboardData.ab_test.B;
        renderFunnelChart(groupA, groupB, true, totals);
    } else {
        // A/B 데이터 없으면 전체 합산 퍼널
        renderFunnelChart(totals, null, false, totals);
    }

    renderChannelChart(dashboardData.channels || []);
});

function renderFunnelChart(groupA, groupB, isABMode, totals) {
    const ctx = document.getElementById('funnelChart').getContext('2d');

    const funnelSteps = [
        '1. Page View',
        '2. Scroll (25%)',
        '3. Scroll (50%)',
        '4. Scroll (75%)',
        '5. Scroll (100%)',
        '6. CTA Click',
        '7. Form Submitted'
    ];

    const dataA = [
        groupA.views || 0, groupA.scroll_25 || 0, groupA.scroll_50 || 0,
        groupA.scroll_75 || 0, groupA.scroll_100 || 0, groupA.clicks || 0, groupA.leads || 0
    ];

    const datasets = [{
        label: isABMode ? 'Group A (작은 실패)' : 'Total (전체)',
        data: dataA,
        backgroundColor: 'rgba(0, 201, 161, 0.8)',
        borderColor: 'rgba(0, 201, 161, 1)',
        borderWidth: 1,
        borderRadius: 4
    }];

    if (isABMode && groupB) {
        const dataB = [
            groupB.views || 0, groupB.scroll_25 || 0, groupB.scroll_50 || 0,
            groupB.scroll_75 || 0, groupB.scroll_100 || 0, groupB.clicks || 0, groupB.leads || 0
        ];
        datasets.push({
            label: 'Group B (안전한 도전)',
            data: dataB,
            backgroundColor: 'rgba(255, 51, 102, 0.8)',
            borderColor: 'rgba(255, 51, 102, 1)',
            borderWidth: 1,
            borderRadius: 4
        });

        if (totals) {
            const dataTotal = [
                totals.views || 0, totals.scroll_25 || 0, totals.scroll_50 || 0,
                totals.scroll_75 || 0, totals.scroll_100 || 0, totals.clicks || 0, totals.leads || 0
            ];
            datasets.push({
                label: 'Total (합산)',
                data: dataTotal,
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                borderColor: 'rgba(255, 255, 255, 0.4)',
                borderWidth: 1,
                borderDash: [5, 5],
                borderRadius: 4
            });
        }
    }

    // A/B 미지원 시 안내 표시
    const chartTitle = document.querySelector('#funnelChart').closest('.chart-container')?.querySelector('h2');
    if (chartTitle && !isABMode) {
        chartTitle.textContent = 'Funnel (전체 합산 · A/B 대기중)';
    }

    new Chart(ctx, {
        type: 'bar',
        data: { labels: funnelSteps, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#ffffff' }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) { label += ': '; }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toLocaleString();
                                if (context.dataIndex > 0) {
                                    const initialViews = context.dataset.data[0];
                                    if (initialViews > 0) {
                                        const rate = ((context.parsed.y / initialViews) * 100).toFixed(1);
                                        label += ` (${rate}% of initial)`;
                                    }
                                }
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#a0a0ab' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#a0a0ab' }
                }
            }
        }
    });
}

function renderChannelChart(channelsData) {
    const ctx = document.getElementById('channelChart').getContext('2d');

    if (!channelsData || channelsData.length === 0) {
        const chartTitle = ctx.canvas.closest('.chart-container')?.querySelector('h2');
        if (chartTitle) chartTitle.textContent = 'Acquisition Channels (데이터 없음)';
        return;
    }

    // Sort and take top 5
    const topChannels = [...channelsData]
        .sort((a, b) => b.users - a.users)
        .slice(0, 5);

    const labels = topChannels.map(c => c.source);
    const data = topChannels.map(c => c.users);

    const backgroundColors = [
        '#00C9A1', '#33E0C1', '#009F81', '#1A7A66', '#0A4A3D'
    ];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#a0a0ab', font: { size: 12 } }
                }
            },
            cutout: '60%'
        }
    });
}
