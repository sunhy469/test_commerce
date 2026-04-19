const API = '';
let filters = { country: '', rank: 'sales', time: 'daily' };
let chatSession = '';
let voice = null;
let pendingChatMessage = '';
let chatScene = 'auto';
let chatTaskItems = [];
let localChatSessions = [];
let activeSessionId = '';
const dashboardMiniCharts = {};

document.addEventListener('DOMContentLoaded', () => { loadDashboard(); initSellerCenterPages(); loadPaymentChannels(); initLocalChats(); bindOutsideClickForTools(); bindChatInputShortcuts(); bindListingEntryTrigger(); loadChatHistory(); });

function go(page) {
    if (page === 'listing') {
        openListingModal();
        return;
    }
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const targetPage = document.getElementById('page-' + page);
    if (!targetPage) return;
    targetPage.classList.add('active');
    const nav = document.querySelector(`[data-page="${page}"]`);
    if (nav) nav.classList.add('active');
    if (page === 'dashboard') loadDashboard();
    if (page === 'orders') loadOrdersPage();
    if (page === 'products') loadProductsPage();
    if (page === 'contentlive') loadContentLivePage();
    if (page === 'affiliate') loadAffiliatePage();
    if (page === 'logistics') loadLogisticsPage();
    if (page === 'finance') loadFinancePage();
    if (page === 'health') loadHealthPage();
    if (page === 'messages') loadMessagesPage();
    if (page === 'settings') loadSettingsPage();
    if (page === 'ranking') loadRanking();
    if (page === 'chat') loadChatHistory();
    if (page === 'purchase') loadOrders();
    updateSidebarHistoryVisibility(page);
}

async function loadDashboard() {
    const root = document.getElementById('sellerDashboardRoot');
    if (!root) return;
    root.innerHTML = loadingSkeleton('Dashboard 数据加载中...');
    let data = buildMockSellerData();
    try {
        const [stats, acts, favs, stores, orders] = await Promise.all([
            fetch(API + '/api/history/stats').then(r => r.json()),
            fetch(API + '/api/history/activities?limit=80').then(r => r.json()),
            fetch(API + '/api/history/favorites?limit=100').then(r => r.json()),
            fetch(API + '/api/user/store-bindings').then(r => r.json()),
            fetch(API + '/api/purchase/orders').then(r => r.json()),
        ]);
        data = mapSellerData({ stats, acts, favs, stores, orders });
    } catch (e) {
        data.state = 'mock';
    }

    root.innerHTML = renderDashboardPage(data);
    renderDashboardCharts(data);
}

function build7DayTrend(activities) {
    const days = [];
    const counts = new Map();
    for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const key = d.toISOString().slice(0, 10);
        days.push(key.slice(5));
        counts.set(key, 0);
    }
    for (const a of activities) {
        const raw = a.created_at || a.timestamp || '';
        const key = String(raw).slice(0, 10);
        if (counts.has(key)) counts.set(key, (counts.get(key) || 0) + 1);
    }
    return { dates: days, values: [...counts.values()] };
}


function initSellerCenterPages() {
    loadOrdersPage();
    loadProductsPage();
    loadContentLivePage();
    loadAffiliatePage();
    loadLogisticsPage();
    loadFinancePage();
    loadHealthPage();
    loadMessagesPage();
    loadSettingsPage();
}

function loadingSkeleton(text = 'Loading...') { return `<div class="section-card p-6 text-sm text-[var(--muted)]">${text}</div>`; }
function emptyState(title, desc) { return `<div class="section-card p-8 text-center text-sm text-[var(--muted)]"><div class="font-semibold text-[var(--text)]">${title}</div><div class="mt-2">${desc}</div></div>`; }
function statusTag(type, text) { return `<span class="status-tag ${type}">${escapeHtml(text)}</span>`; }
function sectionCard(title, subtitle, content) { return `<section class="section-card p-5"><div class="flex items-start justify-between mb-4"><div><h3 class="text-lg font-bold">${title}</h3><div class="text-xs text-[var(--muted)] mt-1">${subtitle || ''}</div></div></div>${content}</section>`; }

function renderFilterBar() {
    return `<section class="section-card p-4"><div class="flex flex-wrap items-center gap-2 text-sm"><select class="rounded-xl border px-3 py-2 bg-white" id="dashTimeRange"><option>今日</option><option selected>近7天</option><option>近30天</option><option>自定义</option></select><select class="rounded-xl border px-3 py-2 bg-white"><option>全部店铺</option><option>TradeAgent US</option><option>TradeAgent SEA</option></select><select class="rounded-xl border px-3 py-2 bg-white"><option>Global</option><option>US</option><option>UK</option><option>ID</option></select><button class="action-btn" onclick="loadDashboard()">刷新数据</button><button class="action-btn">导出报表</button><div class="ml-auto text-xs text-[var(--muted)]">Seller Center · 经营驾驶舱</div></div></section>`;
}

function renderDashboardPage(data) {
    const kpi = data.kpi.map(item => `<div class="soft-card p-4 rounded-2xl"><div class="text-xs text-[var(--muted)]">${item.name}</div><div class="text-2xl font-black mt-2">${item.value}</div><div class="flex justify-between items-center mt-2"><span class="text-xs ${item.trend >= 0 ? 'text-emerald-700' : 'text-red-600'}">${item.trend >= 0 ? '↑' : '↓'} ${Math.abs(item.trend)}%</span><canvas id="spark_${item.key}" height="32"></canvas></div></div>`).join('');
    const todos = data.todos.map(t => `<div class="flex items-center justify-between border-b border-[rgba(126,96,60,.1)] py-2"><span class="text-sm">${t.name}</span><span class="font-semibold">${t.value}</span></div>`).join('');
    const topProducts = data.topProducts.map((p,i) => `<div class="flex items-center justify-between py-2 border-b border-[rgba(126,96,60,.1)]"><span>${i+1}. ${p.name}</span><span class="text-[var(--accent-strong)]">${p.gmv}</span></div>`).join('');
    return `${renderFilterBar()}<section class="section-card p-5"><div class="flex justify-between"><div><h2 class="serif-title text-3xl font-black">Seller Center Dashboard</h2><p class="text-sm text-[var(--muted)] mt-1">经营、履约、财务、内容一体化总览</p></div>${data.state==='mock'?'<span class="status-tag warn">Mock Fallback</span>':''}</div><div class="seller-grid-kpi mt-4">${kpi}</div></section><div class="grid xl:grid-cols-3 gap-4"><section class="section-card p-5 xl:col-span-2"><h3 class="font-bold mb-3">GMV / 订单 / 买家趋势</h3><canvas id="chartTrend" height="120"></canvas></section><section class="section-card p-5"><h3 class="font-bold mb-3">收入构成</h3><canvas id="chartRevenueMix" height="160"></canvas></section></div><div class="grid xl:grid-cols-3 gap-4"><section class="section-card p-5"><h3 class="font-bold mb-3">流量来源</h3><canvas id="chartTraffic" height="140"></canvas></section><section class="section-card p-5"><h3 class="font-bold mb-3">订单状态分布</h3><canvas id="chartOrderStatus" height="140"></canvas></section><section class="section-card p-5"><h3 class="font-bold mb-3">店铺健康度</h3><div class="text-4xl font-black">${data.health.score}</div><div class="text-xs text-[var(--muted)] mt-2">违规率低于行业均值 ${data.health.delta}%</div></section></div><div class="grid xl:grid-cols-2 gap-4">${sectionCard('热销商品 Top10','GMV 排行',topProducts)}${sectionCard('待办与预警','订单、退款、库存、违规',todos)}</div>`;
}

function renderDashboardCharts(data) {
    renderTrendChart('chartTrend', data.trendLabels, [
        { label: 'GMV', data: data.trendGmv, borderColor: '#b84520' },
        { label: '订单数', data: data.trendOrders, borderColor: '#2f5d50' },
        { label: '买家数', data: data.trendBuyers, borderColor: '#3b82f6' },
    ]);
    renderPieChart('chartRevenueMix', data.revenueMix);
    renderBarChart('chartTraffic', data.trafficSources);
    renderDoughnut('chartOrderStatus', data.orderStates);
    data.kpi.forEach(item => renderSparkline(`spark_${item.key}`, item.spark));
}

function renderTrendChart(id, labels, datasets) {
    const el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: 'line', data: { labels, datasets: datasets.map(d => ({ ...d, fill: false, tension: .3 })) }, options: { responsive: true, plugins: { legend: { display: true } } } });
}
function renderPieChart(id, data) { const el = document.getElementById(id); if (!el) return; new Chart(el, { type: 'doughnut', data: { labels: data.map(i=>i.name), datasets: [{ data: data.map(i=>i.value), backgroundColor:['#b84520','#2f5d50','#8b5cf6','#f59e0b'] }] } }); }
function renderBarChart(id, data) { const el = document.getElementById(id); if (!el) return; new Chart(el, { type: 'bar', data: { labels: data.map(i=>i.name), datasets: [{ data: data.map(i=>i.value), backgroundColor:'#2f5d50' }] } }); }
function renderDoughnut(id, data) { const el = document.getElementById(id); if (!el) return; new Chart(el, { type: 'doughnut', data: { labels: data.map(i=>i.name), datasets: [{ data: data.map(i=>i.value), backgroundColor:['#f59e0b','#3b82f6','#10b981','#ef4444'] }] } }); }
function renderSparkline(id, data) { const el = document.getElementById(id); if (!el) return; new Chart(el, { type: 'line', data: { labels: data.map((_,i)=>i+1), datasets: [{ data, borderColor:'#b84520', pointRadius:0, tension:.35 }] }, options: { responsive:true, plugins:{legend:{display:false}, tooltip:{enabled:false}}, scales:{x:{display:false},y:{display:false}} } }); }

function buildMockSellerData() {
    const labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    return {
        state: 'normal', trendLabels: labels, trendGmv:[12,16,14,19,24,21,28], trendOrders:[60,72,68,83,90,88,102], trendBuyers:[45,52,50,63,71,69,80],
        kpi: [
            { key:'gmv', name:'GMV', value:'$128,930', trend:12.4, spark:[10,11,9,12,13,14,15] },
            { key:'paidOrders', name:'支付订单数', value:'1,284', trend:8.2, spark:[7,8,8,9,9,10,11] },
            { key:'buyers', name:'支付买家数', value:'1,038', trend:6.7, spark:[6,6,7,7,8,8,9] },
            { key:'aov', name:'客单价', value:'$100.4', trend:1.9, spark:[8,9,8,9,10,9,10] },
            { key:'cvr', name:'支付转化率', value:'4.8%', trend:0.8, spark:[4,4.1,4.1,4.3,4.4,4.6,4.8] },
            { key:'refund', name:'退款率', value:'1.6%', trend:-0.4, spark:[2.3,2.1,2.1,1.9,1.8,1.7,1.6] },
            { key:'pending', name:'待处理订单', value:'96', trend:-3.3, spark:[130,121,118,108,103,99,96] },
            { key:'settle', name:'待结算金额', value:'$19,460', trend:5.6, spark:[13,13,14,15,16,18,19] },
        ],
        revenueMix:[{name:'商品收入',value:62},{name:'直播收入',value:18},{name:'达人带货',value:13},{name:'广告带动',value:7}],
        trafficSources:[{name:'短视频',value:38},{name:'直播',value:24},{name:'商品卡',value:15},{name:'达人',value:12},{name:'自然',value:7},{name:'广告',value:4}],
        orderStates:[{name:'待发货',value:32},{name:'运输中',value:41},{name:'已完成',value:180},{name:'异常',value:9}],
        health:{score:92,delta:14},
        topProducts:[{name:'Air Mesh Shoes',gmv:'$8,740'},{name:'Portable Blender',gmv:'$7,990'},{name:'LED Clip Light',gmv:'$7,120'}],
        todos:[{name:'待发货订单',value:32},{name:'退款申请',value:7},{name:'低库存商品',value:12},{name:'异常物流',value:5},{name:'违规提醒',value:2}],
    };
}

function mapSellerData({ stats, acts, favs, stores, orders }) {
    const mock = buildMockSellerData();
    const trend = build7DayTrend(acts.activities || []);
    const bindings = stores.stores || [];
    mock.kpi[1].value = String((orders.orders || []).length || mock.kpi[1].value);
    mock.kpi[2].value = String((favs.favorites || []).length || mock.kpi[2].value);
    mock.kpi[6].value = String((orders.orders || []).filter(o => (o.workflow_stage || '').includes('draft')).length || mock.kpi[6].value);
    mock.trendLabels = trend.dates;
    mock.trendOrders = trend.values.map(v => v + 50);
    mock.kpi.push({ key:'store', name:'店铺数', value:String(bindings.length), trend:2.1, spark:[1,1,2,2,3,3,bindings.length || 3] });
    return mock;
}

function renderSimpleModule(rootId, title, subtitle, cards, tableHeaders, tableRows) {
    const root = document.getElementById(rootId); if (!root) return;
    const cardHtml = cards.map(c => `<div class="soft-card rounded-2xl p-4"><div class="text-xs text-[var(--muted)]">${c.label}</div><div class="text-2xl font-black mt-1">${c.value}</div></div>`).join('');
    const rows = tableRows.map(r => `<tr>${r.map(v => `<td>${v}</td>`).join('')}</tr>`).join('');
    root.innerHTML = `<section class="section-card p-5"><h2 class="serif-title text-3xl font-bold">${title}</h2><p class="text-sm text-[var(--muted)] mt-1">${subtitle}</p><div class="seller-grid-kpi mt-4">${cardHtml}</div></section><section class="section-card p-5 mt-4 overflow-auto"><table class="data-table"><thead><tr>${tableHeaders.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></section>`;
}

function loadOrdersPage() {
    renderSimpleModule('ordersPageRoot', '订单管理 Orders', '多条件筛选、状态标签、异常面板（已保留原采购接口）',
        [{label:'待发货',value:'32'},{label:'超时发货风险',value:'6'},{label:'退款申请',value:'7'},{label:'异常物流',value:'5'}],
        ['订单号','商品信息','买家','实付金额','数量','订单状态','支付','发货','售后','下单时间','操作'],
        [['TK20260419001','Air Mesh Shoes / SKU-M1','Mia', '$129', '1', statusTag('warn','待发货'), statusTag('success','已支付'), statusTag('warn','待揽收'), statusTag('info','无'), '2026-04-19 10:20','查看'],['TK20260419002','Portable Blender / SKU-B8','Noah', '$88', '2', statusTag('success','已完成'), statusTag('success','已支付'), statusTag('success','已签收'), statusTag('info','关闭'), '2026-04-19 09:05','展开']]);
}
function loadProductsPage() {
    renderSimpleModule('productsPageRoot', '商品管理 Products', '商品总览、商品列表、库存管理、质量建议',
        [{label:'上架商品',value:'286'},{label:'低库存预警',value:'12'},{label:'审核中',value:'9'},{label:'违规商品',value:'2'}],
        ['主图','标题','类目','价格区间','库存','销量','曝光','点击率','转化率','状态','操作'],
        [['🖼️','Air Mesh Shoes','Shoes','$89-$129','42','1,248','80k','3.6%','4.8%',statusTag('success','上架'),'编辑'],['🖼️','LED Clip Light','Home','$12-$19','8','3,012','160k','2.8%','2.1%',statusTag('warn','低库存'),'补货']]);
}
function loadContentLivePage() { renderSimpleModule('contentLivePageRoot', '内容与直播 Content/LIVE', '短视频与直播带货分析', [{label:'视频带货GMV',value:'$46,920'},{label:'视频CTR',value:'3.9%'},{label:'直播场次',value:'24'},{label:'直播GMV',value:'$32,840'}], ['维度','指标','值','备注'], [['短视频','CTOR','2.4%','周同比+0.2%'],['直播','平均停留时长','2m 18s','高于类目均值']]); }
function loadAffiliatePage() { renderSimpleModule('affiliatePageRoot', '联盟带货 Affiliate', '达人 / 商品 / 视频 / 直播多维分析', [{label:'达人数',value:'86'},{label:'达人GMV',value:'$39,200'},{label:'达人佣金',value:'$6,820'},{label:'合作中',value:'53'}], ['达人','带货商品','GMV','佣金','状态'], [['@luna_live','17','$8,420','$1,320',statusTag('success','合作中')],['@techdaisy','8','$4,780','$690',statusTag('info','观察')]]); }
function loadLogisticsPage() { renderSimpleModule('logisticsPageRoot', '物流履约 Logistics', 'SLA 风险、仓库表现、物流异常', [{label:'On-time Delivery',value:'96.2%'},{label:'3-Day Delivery',value:'91.4%'},{label:'Late Dispatch',value:'2.1%'},{label:'Valid Tracking',value:'99.1%'}], ['仓库','包裹量','准时率','异常数','风险'], [['US-WH1','8,420','97.1%','42',statusTag('success','低')],['SEA-WH2','5,180','93.8%','76',statusTag('warn','中')]]); }
function loadFinancePage() { renderSimpleModule('financePageRoot', '财务结算 Finance', '收入、结算、退款与可提现管理', [{label:'On Hold',value:'$4,820'},{label:'Processing',value:'$12,430'},{label:'Paid',value:'$108,420'},{label:'可提现',value:'$76,280'}], ['结算单号','周期','应结算','平台费用','状态'], [['ST202604-1','04/01-04/07','$23,400','$1,120',statusTag('success','已打款')],['ST202604-2','04/08-04/14','$26,800','$1,340',statusTag('info','处理中')]]); }
function loadHealthPage() { renderSimpleModule('healthPageRoot', '店铺健康 Shop Health', '评分 + 指标诊断 + 违规记录 + Top Opportunity', [{label:'健康分',value:'92'},{label:'商品满意度',value:'4.7/5'},{label:'客服体验',value:'95%'},{label:'违规记录',value:'2'}], ['模块','当前值','阈值','建议'], [['物流履约','93.8%','>=95%',statusTag('warn','提升海外仓备货')],['退款率','1.6%','<=2.0%',statusTag('success','保持')]]); }
function loadMessagesPage() { renderSimpleModule('messagesPageRoot', '客户消息 Messages', '售前咨询、售后工单与SLA', [{label:'未读会话',value:'28'},{label:'待处理售后',value:'13'},{label:'平均响应',value:'4m 12s'},{label:'满意度',value:'95%'}], ['会话ID','用户','类型','状态','更新时间'], [['MSG-1021','Olivia','售前咨询',statusTag('info','处理中'),'10:21'],['MSG-1022','Lucas','退款咨询',statusTag('warn','待响应'),'10:08']]); }
function loadSettingsPage() { renderSimpleModule('settingsPageRoot', '设置 Settings', '账号权限、偏好与自动化规则', [{label:'角色数',value:'8'},{label:'已启用自动化',value:'12'},{label:'API Token',value:'3'},{label:'告警规则',value:'16'}], ['配置项','值','状态'], [['默认站点','US',statusTag('success','启用')],['风险告警','订单异常/违规/低库存',statusTag('success','启用')]]); }

function setChatScene(scene) {
    const allowed = ['auto', 'ranking', 'supply', 'detail', 'image'];
    chatScene = allowed.includes(scene) ? scene : 'auto';
    document.querySelectorAll('#chatSceneChips .chip').forEach(c => c.classList.toggle('on', c.dataset.scene === chatScene));
    const modeLabel = document.getElementById('chatModeLabel');
    if (modeLabel) modeLabel.textContent = sceneLabel(chatScene);
}

function quickCommand(text) {
    go('chat');
    document.getElementById('chatInput').value = text;
    document.getElementById('chatCommandSummary') && (document.getElementById('chatCommandSummary').textContent = '已载入快捷任务');
    prepareChat();
}

function autoPolishPrompt(raw, scene, country) {
    const text = (raw || '').trim();
    if (!text) return '';
    if (!country) return text;
    return `${text}（目标市场：${country}）`;
}

function fillChatTemplate() {
    const input = document.getElementById('chatInput');
    const country = document.getElementById('chatCountry')?.value || '目标国家';
    const templates = {
        auto: `请用简单方式解释：___`,
        ranking: `帮我总结一下${country}市场最近的品类趋势`,
        supply: `我想做一个新品，请给我 3 个选品方向`,
        detail: `帮我把这段产品描述优化成更容易理解的文案`,
        image: `给我一个商品主图提示词，风格干净简洁`
    };
    input.value = templates[chatScene] || templates.auto;
    input.focus();
}

function handleChatImage(inp) {
    const file = inp.files?.[0];
    document.getElementById('chatAttachmentLabel').textContent = file ? `已上传：${file.name}` : '';
}

function prepareChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;
    const country = document.getElementById('chatCountry')?.value;
    const polished = autoPolishPrompt(msg, chatScene, country);
    pendingChatMessage = polished;
    const summary = document.getElementById('chatCommandSummary');
    if (summary) summary.textContent = `待发送：普通对话`;
    sendChat(pendingChatMessage);
    pendingChatMessage = '';
}


function sceneLabel(scene) {
    return ({ auto:'自动模式', ranking:'热销榜', supply:'1688找货', detail:'详情页', image:'图像生成' })[scene] || '自动模式';
}

async function sendChat(overrideMsg = '') {
    const inp = document.getElementById('chatInput');
    const msg = (overrideMsg || inp.value).trim();
    if (!msg) return;
    inp.value = '';
    addMsg('user', msg);
    persistChatMessage('user', msg);
    addMsg('ai', '思考中...', 'thinking');
    try {
        const res = await fetch(API + '/api/chat', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                session_id: chatSession,
                country: document.getElementById('chatCountry')?.value || '',
                scene: chatScene,
                attachment_name: document.getElementById('chatImage')?.files?.[0]?.name || ''
            })
        });
        const d = await res.json();
        chatSession = d.session_id || chatSession;
        const active = localChatSessions.find(s => s.id === activeSessionId);
        if (active) {
            active.backend_session_id = chatSession;
            saveLocalChats();
        }
        document.getElementById('thinking')?.remove();
        addMsg('ai', d.reply || '完成');
        persistChatMessage('assistant', d.reply || '完成');
        if (d.data) showChatData(d.data);
    } catch (e) {
        document.getElementById('thinking')?.remove();
        addMsg('ai', '请求失败: ' + e.message);
        persistChatMessage('assistant', '请求失败: ' + e.message);
    }
}

function addMsg(role, text, id) {
    const box = document.getElementById('chatMessages');
    const welcome = box.querySelector('.text-center'); if (welcome) welcome.remove();
    const div = document.createElement('div');
    div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'}`;
    if (id) div.id = id;
    div.innerHTML = `<div class="max-w-[82%] px-4 py-3 text-sm ${role === 'user' ? 'bubble-user' : 'bubble-ai'}">${escapeHtml(text)}</div>`;
    box.appendChild(div); box.scrollTop = box.scrollHeight;
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/\n/g, '<br>');
}

function pushTaskQueue(task) {
    chatTaskItems.unshift({ ...task, createdAt: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) });
    chatTaskItems = chatTaskItems.slice(0, 5);
    renderTaskQueue();
}

function renderTaskQueue() {
    const box = document.getElementById('chatTaskQueue');
    const count = document.getElementById('chatQueueCount');
    if (!box) return;
    if (count) count.textContent = `${chatTaskItems.length} 条任务`;
    if (!chatTaskItems.length) {
        box.innerHTML = '<div class="rounded-2xl border bg-white p-3">暂无任务，输入后自动加入队列。</div>';
        return;
    }
    box.innerHTML = chatTaskItems.map((task, idx) => `<div class="rounded-2xl border bg-white p-3"><div class="flex items-center justify-between gap-3"><div class="font-medium truncate pr-3">${escapeHtml(task.title)}</div><span class="text-[11px] px-2 py-1 rounded-full ${idx === 0 ? 'bg-[rgba(184,69,32,.08)] text-[var(--accent-strong)]' : 'bg-[rgba(15,23,42,.05)] text-[var(--muted)]'}">${escapeHtml(task.status || 'queued')}</span></div><div class="text-xs text-[var(--muted)] mt-2">${escapeHtml(task.country || '全部国家')} · ${escapeHtml(task.createdAt || '')}</div></div>`).join('');
}

function updateModuleLights(data) {
    const box = document.getElementById('chatModuleLights');
    if (!box) return;
    const stepMap = {};
    (data?.steps || []).forEach(step => { stepMap[step.module] = step.status || 'ready'; });
    const items = [
        { key: 'ranking', label: '热销榜' },
        { key: 'supply', label: '供应链' },
        { key: 'detail', label: '详情页' },
        { key: 'image', label: '商品图' },
    ];
    box.innerHTML = items.map(item => {
        const status = stepMap[item.key] || 'pending';
        const color = status === 'done' ? 'bg-emerald-500' : status === 'ready' ? 'bg-amber-400' : 'bg-slate-300';
        const text = status === 'done' ? '已完成' : status === 'ready' ? '已就绪' : '待执行';
        return `<div class="rounded-2xl border bg-white p-3"><div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full ${color}"></span><span>${item.label}</span></div><div class="text-xs text-[var(--muted)] mt-2">${text}</div></div>`;
    }).join('');
}

function renderSelectedProduct(product) {
    const box = document.getElementById('chatSelectedProduct');
    const label = document.getElementById('chatSelectedLabel');
    if (!box) return;
    if (!product) {
        if (label) label.textContent = '未选择';
        box.innerHTML = '执行后自动选中当前商品。';
        return;
    }
    if (label) label.textContent = product.title || '已选中';
    box.innerHTML = `<div class="grid grid-cols-[72px_1fr] gap-4 items-start"><img src="${product.image_url || 'https://picsum.photos/seed/current-product/72/72'}" class="w-[72px] h-[72px] rounded-2xl object-cover bg-gray-100"><div><div class="font-semibold">${escapeHtml(product.title || '商品')}</div><div class="grid grid-cols-2 gap-3 mt-3 text-sm"><div><div class="text-[11px] text-[var(--muted)]">价格</div><div class="font-semibold">$${escapeHtml(product.price ?? 0)}</div></div><div><div class="text-[11px] text-[var(--muted)]">国家</div><div class="font-semibold">${escapeHtml(product.country || '—')}</div></div><div><div class="text-[11px] text-[var(--muted)]">日销量</div><div class="font-semibold">${escapeHtml(product.daily_sales ?? 0)}</div></div><div><div class="text-[11px] text-[var(--muted)]">近7天销量</div><div class="font-semibold">${escapeHtml(product.weekly_sales ?? 0)}</div></div></div></div></div>`;
}

function renderAssetStatus(data) {
    const box = document.getElementById('chatAssetStatus');
    if (!box) return;
    const hasPage = !!data?.page;
    const hasImage = !!data?.image;
    const tags = buildSuggestedTags(data);
    box.innerHTML = [
        { label: '详情页', status: hasPage ? '已生成' : '待生成' },
        { label: '商品图', status: hasImage ? '已生成' : '待生成' },
        { label: '标签', status: tags.length ? `${tags.length} 个` : '待生成' },
    ].map(item => `<div class="rounded-2xl border bg-white/70 p-3"><div class="text-[11px] text-[var(--muted)]">${item.label}</div><div class="font-semibold mt-2">${item.status}</div></div>`).join('');
}

function buildSuggestedTags(data) {
    const product = data?.selected_product || data?.product || (data?.products || [])[0] || {};
    const parts = [product.category, product.country, product.title].filter(Boolean).join(' ');
    const tokens = parts.split(/\s+/).filter(Boolean).slice(0, 5);
    return [...new Set(tokens)].slice(0, 5);
}

function renderNextActions(data) {
    const box = document.getElementById('chatNextActions');
    if (!box) return;
    const product = data?.selected_product || data?.product || (data?.products || [])[0] || {};
    const tags = buildSuggestedTags(data);
    const actions = [
        product.title ? `为「${product.title}」生成商品详情页` : '生成商品详情页',
        product.title ? `为「${product.title}」生成商品图` : '生成商品图',
        tags.length ? `补充售卖 tag：${tags.join(' / ')}` : '补充售卖 tag',
        '上架到新平台店铺',
    ];
    box.innerHTML = actions.map(action => `<div class="rounded-2xl border bg-white/70 p-4">${escapeHtml(action)}</div>`).join('');
}

function showChatData(data) {
    if (!data) return;
    let html = '';
    if (data.type === 'products' && data.products) {
        html = `<div class="p-3 bg-white rounded-2xl border text-xs mt-1"><p class="font-medium mb-2">找到 ${data.products.length} 个商品</p>${data.products.slice(0, 4).map(p => `<div class="flex justify-between py-1"><span class="truncate pr-2">${escapeHtml(p.title)}</span><span class="text-[var(--accent-strong)]">$${p.price}</span></div>`).join('')}</div>`;
    } else if (data.type === 'suppliers' && data.suppliers) {
        html = `<div class="p-3 bg-white rounded-2xl border text-xs mt-1"><p class="font-medium mb-2">匹配 ${data.suppliers.length} 个供应商</p>${data.suppliers.slice(0, 3).map(s => `<div class="py-1">${escapeHtml(s.supplier_name || s.name)} - ¥${s.price || s.unit_price || '?'}</div>`).join('')}</div>`;
    } else if (data.type === 'detail_page') {
        const preview = data.html_page?.preview_url ? `<a href="${data.html_page.preview_url}" target="_blank" class="underline text-[var(--accent-strong)]">打开详情页预览</a>` : '详情页已生成';
        html = `<div class="p-3 bg-emerald-50 rounded-2xl border text-xs mt-1 text-emerald-700"><div class="font-medium mb-1">${escapeHtml(data.product?.title || '商品')}</div><div>${preview}</div></div>`;
    } else if (data.type === 'image') {
        html = `<div class="p-3 bg-sky-50 rounded-2xl border text-xs mt-1 text-sky-800"><div class="font-medium mb-1">图像任务已准备</div><div>${escapeHtml(data.prompt || data.message || '可前往内容生成模块继续细化。')}</div></div>`;
    } else if (data.type === 'workflow') {
        const steps = (data.steps || []).map(step => `<div class="flex justify-between gap-3 py-1"><span>${escapeHtml(step.summary || step.module)}</span><span class="text-[var(--muted)]">${escapeHtml(step.status || '')}</span></div>`).join('');
        const preview = data.html_page?.preview_url ? `<a href="${data.html_page.preview_url}" target="_blank" class="underline text-[var(--accent-strong)]">查看详情页</a>` : '';
        html = `<div class="p-3 bg-white rounded-2xl border text-xs mt-1 space-y-2"><p class="font-medium">自动化任务结果</p>${steps ? `<div>${steps}</div>` : ''}${preview ? `<div>${preview}</div>` : ''}</div>`;
    }
    if (html) {
        const box = document.getElementById('chatMessages');
        const d = document.createElement('div'); d.className = 'flex justify-start';
        d.innerHTML = `<div class="max-w-[82%]">${html}</div>`;
        box.appendChild(d); box.scrollTop = box.scrollHeight;
    }

    const selected = data?.selected_product || data?.product || (data?.products || [])[0] || null;
    if (chatTaskItems.length) {
        chatTaskItems[0].status = 'done';
        renderTaskQueue();
    }
    updateModuleLights(data);
    renderSelectedProduct(selected);
    renderAssetStatus(data);
    renderNextActions({ ...data, selected_product: selected });
    renderChatWorkflow(data);
    renderChatAutoResults(data);
}

function renderChatWorkflow(data) {
    const board = document.getElementById('chatWorkflowBoard');
    const stepCount = document.getElementById('chatStepCount');
    if (!board) return;
    const steps = data?.steps || [];
    if (stepCount) stepCount.textContent = steps.length || (data?.products?.length ? 1 : 0);
    if (!steps.length) {
        board.innerHTML = `<div class="rounded-2xl border bg-white/70 p-4 text-[var(--muted)]">当前请求未返回多步骤执行流，等待自动化任务结果。</div>`;
        return;
    }
    board.innerHTML = steps.map((step, idx) => `<div class="rounded-2xl border bg-white/80 p-4"><div class="flex items-center justify-between gap-3"><div><div class="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">STEP ${idx + 1}</div><div class="font-semibold mt-1">${escapeHtml(step.module || 'module')}</div></div><span class="px-2 py-1 rounded-full bg-[rgba(47,93,80,.08)] text-[var(--forest)] text-[11px]">${escapeHtml(step.status || 'ready')}</span></div><div class="text-sm text-[var(--muted)] mt-2">${escapeHtml(step.summary || '')}</div></div>`).join('');
}

function renderChatAutoResults(data) {
    const container = document.getElementById('chatAutoResults');
    const countEl = document.getElementById('chatAutoCount');
    if (!container) return;
    const products = data?.products || [];
    if (countEl) countEl.textContent = products.length || 0;
    if (!products.length) {
        container.innerHTML = `<div class="rounded-2xl border bg-white/70 p-4">执行后将在此生成自动化候选商品结果卡。</div>`;
        return;
    }
    container.innerHTML = products.slice(0, 8).map((p, i) => renderAutoProductCard(p, i)).join('');
}

function renderAutoProductCard(p, i) {
    const img = p.image_url || `https://picsum.photos/seed/chat-${p.product_id || i}/88/88`;
    return `<div class="rounded-[24px] border bg-white/88 p-4"><div class="grid grid-cols-[88px_1fr] gap-4"><img src="${img}" class="w-[88px] h-[88px] rounded-2xl object-cover bg-gray-100" onerror="this.src='https://picsum.photos/seed/fallback-${i}/88/88'"><div class="min-w-0"><div class="font-semibold text-[15px] leading-6">${escapeHtml(p.title || '商品')}</div><div class="grid sm:grid-cols-4 gap-2 mt-3 text-sm"><div><div class="text-[11px] text-[var(--muted)]">价格</div><div class="font-semibold text-[var(--accent-strong)]">$${escapeHtml(p.price ?? 0)}</div></div><div><div class="text-[11px] text-[var(--muted)]">日销量</div><div class="font-semibold">${escapeHtml(p.daily_sales ?? 0)}</div></div><div><div class="text-[11px] text-[var(--muted)]">近7天销量</div><div class="font-semibold">${escapeHtml(p.weekly_sales ?? 0)}</div></div><div><div class="text-[11px] text-[var(--muted)]">国家</div><div class="font-semibold">${escapeHtml(p.country || '—')}</div></div></div></div></div><div class="flex flex-wrap lg:flex-nowrap gap-2 mt-4 justify-end"><button onclick="bindFromRanking('${esc(p.title)}','${p.country || ''}')" class="action-btn">上架店铺</button><button onclick="fillContent('detail','${esc(p.title)}',${p.price || 0},'${esc(p.category || '')}','${p.country || ''}')" class="action-btn">制作商品详情页</button><button onclick="fillContent('image','${esc(p.title)}',${p.price || 0},'${esc(p.category || '')}','${p.country || ''}')" class="action-btn">制作商品图</button><button onclick="addFav('${esc(p.product_id)}','${esc(p.title)}',${p.price || 0},'${esc(p.category || '')}')" class="action-btn">收藏</button></div></div>`;
}

let chatLoaded = false;
async function loadChatHistory() {
    renderLocalHistoryChips();
    if (chatLoaded) return;
    chatLoaded = true;
    const modeLabel = document.getElementById('chatModeLabel');
    if (modeLabel) modeLabel.textContent = sceneLabel(chatScene);
}

function bindChatInputShortcuts() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            prepareChat();
        }
    });
}

// === Ranking ===
function setFilter(type, val) {
    if (type === 'country') {
        filters.country = val;
        document.querySelectorAll('#countryChips .chip').forEach(c => c.classList.toggle('on', c.dataset.v === val));
    } else if (type === 'rank') {
        filters.rank = val;
        document.querySelectorAll('#rankChips .chip').forEach(c => c.classList.toggle('on', c.dataset.v === val));
    } else if (type === 'time') {
        filters.time = val;
        document.querySelectorAll('#timeChips .chip').forEach(c => c.classList.toggle('on', c.dataset.v === val));
    }
    loadRanking();
}

async function loadRanking() {
    const box = document.getElementById('rankingList');
    const category = document.getElementById('rankingCategory')?.value?.trim() || '';
    document.getElementById('rankingMeta').textContent = `当前查看：${filters.country || '全部国家'} / ${filters.rank === 'sales' ? '销量榜' : '飙升榜'} / ${filters.time === 'daily' ? '日榜' : filters.time === 'weekly' ? '近7天' : '月榜'}${category ? ' / 品类：' + category : ''}`;
    box.innerHTML = '<div class="text-center text-[var(--muted)] py-8">加载中...</div>';
    try {
        const res = await fetch(API + '/api/monitor/ranking', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ country: filters.country, rank_type: filters.rank, time_range: filters.time, category, limit: 20 })
        });
        const d = await res.json();
        const ps = d.products || [];
        if (!ps.length) { box.innerHTML = '<div class="text-center text-[var(--muted)] py-8">暂无数据</div>'; return; }
        const flags = { US:'🇺🇸', GB:'🇬🇧', ID:'🇮🇩', TH:'🇹🇭', VN:'🇻🇳', MY:'🇲🇾', PH:'🇵🇭', JP:'🇯🇵', KR:'🇰🇷' };
        box.innerHTML = ps.map((p, i) => {
            const img = p.image_url || `https://picsum.photos/seed/${p.product_id || i}/96/96`;
            const badgeCls = i === 0 ? 'top1' : i === 1 ? 'top2' : i === 2 ? 'top3' : '';
            return `<div class="rank-row soft-card rounded-[24px] p-4 flex flex-col lg:flex-row gap-4">
                <div class="rank-badge ${badgeCls}"><div>TOP</div><div>${i + 1}</div></div>
                <img src="${img}" class="w-full lg:w-24 h-24 rounded-2xl object-cover bg-gray-100" onerror="this.src='https://picsum.photos/seed/${i}/96/96'">
                <div class="flex-1 min-w-0">
                    <div class="flex flex-wrap items-center gap-2 text-xs mb-2"><span>${flags[p.country] || '🌍'}</span><span class="px-2 py-1 rounded-full bg-[rgba(184,69,32,.08)] text-[var(--accent-strong)]">${p.category || '未分类'}</span><span class="px-2 py-1 rounded-full bg-[rgba(47,93,80,.08)] text-[var(--forest)]">${filters.rank === 'sales' ? '销量榜' : '飙升榜'}</span></div>
                    <h4 class="text-base font-semibold leading-6">${p.title}</h4>
                    <div class="grid md:grid-cols-4 gap-2 mt-3 text-sm">
                        <div><div class="text-[var(--muted)] text-xs">价格</div><div class="font-semibold text-[var(--accent-strong)]">$${p.price || 0}</div></div>
                        <div><div class="text-[var(--muted)] text-xs">日销量</div><div class="font-semibold">${p.daily_sales || 0}</div></div>
                        <div><div class="text-[var(--muted)] text-xs">近7天销量</div><div class="font-semibold">${p.weekly_sales || 0}</div></div>
                        <div><div class="text-[var(--muted)] text-xs">总销量</div><div class="font-semibold">${p.sales_count || 0}</div></div>
                    </div>
                </div>
                <div class="flex flex-wrap lg:flex-col gap-2 shrink-0">
                    <button onclick="bindFromRanking('${esc(p.title)}','${p.country || ''}')" class="action-btn">上架店铺</button>
                    <button onclick="fillContent('detail','${esc(p.title)}',${p.price || 0},'${esc(p.category || '')}','${p.country || ''}')" class="action-btn">制作商品详情页</button>
                    <button onclick="fillContent('image','${esc(p.title)}',${p.price || 0},'${esc(p.category || '')}','${p.country || ''}')" class="action-btn">制作商品图</button>
                    <button onclick="addFav('${esc(p.product_id)}','${esc(p.title)}',${p.price || 0},'${esc(p.category)}')" class="action-btn">收藏</button>
                </div>
            </div>`;
        }).join('');
    } catch (e) { box.innerHTML = '<div class="text-center text-red-400 py-8">加载失败</div>'; }
}

function esc(s) { return (s || '').replace(/'/g, "\\'").replace(/"/g, '&quot;'); }

function fillContent(type, title, price, category = '', country = '') {
    openListingModal({ title, price, category, country, focus: type });
}

function bindFromRanking(title, country) {
    openModal('userModal');
    document.getElementById('bName').value = `${title} 店铺任务`;
    if (country && document.getElementById('bCountry')) document.getElementById('bCountry').value = country;
}

async function addFav(pid, title, price, cat) {
    try {
        await fetch(API + '/api/history/favorites', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: pid, title, price, category: cat }) });
        setStatus('已收藏');
    } catch (e) { setStatus('收藏失败'); }
}

async function matchSuppliers() {
    const kw = document.getElementById('supplyKw').value.trim();
    if (!kw) return;
    const box = document.getElementById('supplyResults');
    box.innerHTML = '<div class="text-[var(--accent-strong)]">搜索中...</div>';
    try {
        const res = await fetch(API + '/api/supply/match', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keyword: kw }) });
        const d = await res.json();
        const ss = d.suppliers || [];
        box.innerHTML = ss.length ? ss.map(s => `<div class="soft-card p-4 rounded-2xl"><div class="font-semibold">${s.supplier_name || s.name}</div><div class="text-sm text-[var(--muted)] mt-2">价格：¥${s.price || s.unit_price || s.price_cny || '?'} ｜ MOQ：${s.moq || '?'} ｜ 评分：${s.rating || s.total_score || '-'}</div></div>`).join('') : '<span class="text-[var(--muted)]">未找到</span>';
    } catch (e) { box.innerHTML = '<span class="text-red-400">搜索失败</span>'; }
}

function previewImg(inp) {
    const f = inp.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = e => {
        document.getElementById('imgPreview').innerHTML = `<img src="${e.target.result}" class="w-28 h-28 object-cover rounded-2xl mx-auto mb-2">`;
        document.getElementById('imgHint').textContent = f.name;
    };
    r.readAsDataURL(f);
}

async function imgSearch() {
    const box = document.getElementById('imgResults');
    box.innerHTML = '<div class="text-[var(--accent-strong)]">搜索中...</div>';
    const fd = new FormData();
    const f = document.getElementById('imgFile').files[0];
    if (f) fd.append('image_file', f);
    fd.append('image_url', document.getElementById('imgUrl').value.trim());
    try {
        const res = await fetch(API + '/api/supply/image-search', { method: 'POST', body: fd });
        const d = await res.json();
        const rs = d.results || [];
        box.innerHTML = rs.length ? rs.map(r => `<div class="soft-card p-4 rounded-2xl flex justify-between gap-3"><div><div class="font-semibold">${r.title || '商品'}</div><div class="text-sm text-[var(--muted)] mt-1">图搜匹配结果</div></div><div class="text-[var(--accent-strong)] font-semibold">¥${r.price || '?'}</div></div>`).join('') : '<span class="text-[var(--muted)]">未找到</span>';
    } catch (e) { box.innerHTML = '<span class="text-red-400">搜索失败</span>'; }
}

// === Content Generation ===
function setContentTab(ct) {
    document.querySelectorAll('.ct-panel').forEach(p => p.classList.add('hidden'));
    document.querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    document.getElementById('ct-' + ct).classList.remove('hidden');
    document.querySelector(`[data-ct="${ct}"]`)?.classList.add('active');
}

async function genDetail() {
    const out = document.getElementById('detailOut');
    out.innerHTML = '<div class="text-[var(--accent-strong)] text-sm">生成中...</div>';
    try {
        const res = await fetch(API + '/api/content/detail-page', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product: { title: document.getElementById('dpTitle').value, price: parseFloat(document.getElementById('dpPrice').value) || 9.99, category: document.getElementById('dpCategory').value, description: document.getElementById('dpPrompt').value }, country: document.getElementById('dpCountry').value }) });
        const d = await res.json(); const p = d.page || {};
        const previewLink = d.html_page?.preview_url ? `<a href="${d.html_page.preview_url}" target="_blank" class="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-[rgba(184,69,32,.08)] text-[var(--accent-strong)] text-xs font-semibold">打开 HTML 预览</a>` : '';
        out.innerHTML = `<div class="space-y-4 text-sm"><div class="flex flex-wrap items-center justify-between gap-3"><div class="text-xs text-[var(--muted)]">品类：${escapeHtml(document.getElementById('dpCategory').value || '未填写')}</div>${previewLink}</div>${p.page_title ? `<h3 class="text-xl font-bold">${escapeHtml(p.page_title)}</h3>` : ''}${p.description ? `<p class="text-[var(--muted)] leading-7">${escapeHtml(p.description)}</p>` : ''}${p.bullet_points ? `<ul class="list-disc pl-5 leading-7">${p.bullet_points.map(b => `<li>${escapeHtml(b)}</li>`).join('')}</ul>` : ''}${p.seo_tags ? `<div class="flex flex-wrap gap-2">${p.seo_tags.map(t => `<span class="px-2 py-1 rounded-full bg-[rgba(184,69,32,.08)] text-[var(--accent-strong)] text-xs">${escapeHtml(t)}</span>`).join('')}</div>` : ''}</div>`;
    } catch (e) { out.innerHTML = `<div class="text-red-500 text-sm">失败: ${escapeHtml(e.message)}</div>`; }
}

async function genImage() {
    const out = document.getElementById('imageOut');
    out.innerHTML = '<div class="text-[var(--accent-strong)] text-sm">生成中...</div>';
    try {
        const res = await fetch(API + '/api/content/image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product: { title: document.getElementById('imTitle').value, category: document.getElementById('imCategory').value, description: document.getElementById('imPrompt').value, _image_provider: document.getElementById('imProvider').value, _image_model: document.getElementById('imModel').value, _aspect_ratio: document.getElementById('imAspect').value }, style: document.getElementById('imStyle').value, prompt: `${document.getElementById('imPrompt').value}；目标国家：${document.getElementById('imCountry').value}` }) });
        const d = await res.json();
        const preview = d.html_preview ? `<iframe srcdoc="${d.html_preview.replace(/"/g, '&quot;')}" class="w-full min-h-[420px] rounded-2xl border bg-white"></iframe>` : '';
        out.innerHTML = `<div class="space-y-3 text-sm"><div class="flex flex-wrap items-center justify-between gap-3"><div class="font-semibold">${escapeHtml(d.job_id || '图片任务')}</div><div class="text-xs text-[var(--muted)]">${escapeHtml(d.provider || '')} / ${escapeHtml(d.model || '')}</div></div><div>${escapeHtml(d.message || '已生成')}</div>${d.preview_url ? `<a href="${d.preview_url}" target="_blank" class="inline-flex px-3 py-2 rounded-full text-xs font-semibold bg-[rgba(47,93,80,.08)] text-[var(--forest)]">打开预览页</a>` : ''}${preview || '<div class="border rounded-2xl p-3 bg-white/70 text-[var(--muted)]">暂无预览</div>'}</div>`;
    } catch (e) { out.innerHTML = `<div class="text-red-500 text-sm">失败: ${escapeHtml(e.message)}</div>`; }
}

let currentOrderId = '';
let pendingUnbindId = null;

function previewImageJob() {
    const title = document.getElementById('imTitle').value || '未命名商品';
    const provider = document.getElementById('imProvider').value || 'picset-seed';
    const model = document.getElementById('imModel').value || 'Seed 2.0';
    const aspect = document.getElementById('imAspect').value || '4:5';
    const prompt = document.getElementById('imPrompt').value || '暂无补充 prompt';
    document.getElementById('imageOut').innerHTML = `<div class="space-y-3 text-sm"><div class="text-lg font-semibold">图片任务预览</div><div class="rounded-2xl bg-white/80 border p-4 space-y-2"><div><span class="text-[var(--muted)]">商品：</span>${escapeHtml(title)}</div><div><span class="text-[var(--muted)]">平台：</span>${escapeHtml(provider)}</div><div><span class="text-[var(--muted)]">模型：</span>${escapeHtml(model)}</div><div><span class="text-[var(--muted)]">比例：</span>${escapeHtml(aspect)}</div><div><span class="text-[var(--muted)]">Prompt：</span>${escapeHtml(prompt)}</div></div><div class="text-xs text-[var(--muted)]">确认无误后，再点“确认并生成草稿”。</div></div>`;
}

async function createOrder() {
    try {
        const payload = {
            product_title: document.getElementById('ordProduct').value,
            product_id: document.getElementById('ordProductId').value,
            quantity: parseInt(document.getElementById('ordQty').value) || 1,
            unit_price: parseFloat(document.getElementById('ordPrice').value) || 0,
            customer_name: document.getElementById('ordCustomer').value,
            customer_email: document.getElementById('ordEmail').value,
            shipping_address: document.getElementById('ordAddress').value
        };
        const res = await fetch(API + '/api/purchase/orders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const d = await res.json();
        currentOrderId = d.order?.tiktok_order_id || '';
        renderOrderDetail(d.order);
        setStatus('订单草稿已创建');
        loadOrders();
        loadPaymentChannels();
    } catch (e) { setStatus('创建失败'); }
}

async function loadOrders() {
    try {
        const res = await fetch(API + '/api/purchase/orders'); const d = await res.json();
        const os = d.orders || [];
        document.getElementById('orderList').innerHTML = os.length ? os.map(o => `<button onclick="selectOrder('${esc(o.tiktok_order_id)}')" class="w-full text-left soft-card p-4 rounded-2xl"><div class="flex justify-between gap-3"><span class="font-medium truncate pr-3">${escapeHtml(o.product_title || o.tiktok_order_id || '订单')}</span><span class="text-xs text-[var(--muted)]">${escapeHtml(o.workflow_stage || o.status || '')}</span></div><div class="text-xs text-[var(--muted)] mt-2">订单号：${escapeHtml(o.tiktok_order_id || '')}</div></button>`).join('') : '<span class="text-[var(--muted)]">暂无</span>';
    } catch (e) {}
}

async function selectOrder(orderId) {
    currentOrderId = orderId;
    const res = await fetch(API + `/api/purchase/orders/${orderId}`);
    const d = await res.json();
    renderOrderDetail(d.order);
}

function renderOrderDetail(order) {
    if (!order) return;
    currentOrderId = order.tiktok_order_id || currentOrderId;
    document.getElementById('currentOrderBadge').textContent = currentOrderId || '未选择';
    document.getElementById('payAmount').value = order.purchase_price_cny || order.total_usd || '';
    document.getElementById('payCurrency').value = order.purchase_price_cny ? 'CNY' : 'USD';

    const stageCards = (order.stage_tips || []).map((s, idx) => `<div class="rounded-2xl border p-3 ${s.done ? 'bg-[rgba(47,93,80,.08)] text-[var(--forest)] border-[rgba(47,93,80,.16)]' : 'bg-white/80 text-[var(--muted)] border-[rgba(32,25,19,.06)]'}"><div class="text-[10px] uppercase tracking-[0.16em]">Stage ${idx + 1}</div><div class="mt-1 font-semibold text-sm">${escapeHtml(s.label)}</div></div>`).join('');
    const actions = (order.available_actions || []).length ? (order.available_actions || []).map(a => `<span class="px-2 py-1 rounded-full bg-white border text-[11px]">${escapeHtml(a)}</span>`).join('') : '<span class="text-[var(--muted)]">无</span>';

    document.getElementById('orderWorkflowCard').innerHTML = `<div class="space-y-4"><div class="flex flex-wrap items-center justify-between gap-3"><div><div class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Workflow Snapshot</div><div class="text-xl font-semibold mt-1">${escapeHtml(order.product_title || '订单')}</div><div class="text-xs text-[var(--muted)] mt-1">订单号：${escapeHtml(order.tiktok_order_id || '')}</div></div><div class="px-3 py-1 rounded-full bg-[rgba(184,69,32,.08)] text-[var(--accent-strong)] text-xs font-semibold">${escapeHtml(order.workflow_stage || '')}</div></div><div class="grid md:grid-cols-3 gap-3">${stageCards}</div><div><div class="text-xs uppercase tracking-[0.18em] text-[var(--muted)] mb-2">Available Actions</div><div class="flex flex-wrap gap-2">${actions}</div></div></div>`;

    document.getElementById('orderDetail').innerHTML = `<div class="space-y-3"><div class="grid grid-cols-2 gap-3"><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">客户</div><div class="mt-1 font-semibold">${escapeHtml(order.customer_name || '-')}</div></div><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">邮箱</div><div class="mt-1 font-semibold">${escapeHtml(order.customer_email || '-')}</div></div><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">供应商</div><div class="mt-1 font-semibold">${escapeHtml(order.matched_supplier || order.supplier_id || '-')}</div></div><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">支付通道</div><div class="mt-1 font-semibold">${escapeHtml(order.payment_channel || '-')}</div></div><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">利润预估</div><div class="mt-1 font-semibold">¥${escapeHtml(order.profit_estimate_cny ?? 0)}</div></div><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">支付状态</div><div class="mt-1 font-semibold">${escapeHtml(order.payment_status || '-')}</div></div></div><div class="rounded-2xl bg-white/80 border p-3"><div class="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">备注</div><div class="mt-2 leading-6">${escapeHtml(order.notes || '-')}</div></div></div>`;
}

async function updateOrderStage(status, extra = {}) {
    if (!currentOrderId) { setStatus('请先创建或选择订单'); return; }
    const res = await fetch(API + `/api/purchase/orders/${currentOrderId}/stage`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status, ...extra }) });
    const d = await res.json();
    renderOrderDetail(d.order);
    loadOrders();
}

function confirmStoreStep() { updateOrderStage('store_confirmed', { notes: '已确认店铺绑定，可进入供应商确认。' }); }
function confirmSupplierStep() { updateOrderStage('supplier_confirmed', { supplier_name: '待人工确认供应商', notes: '已确认供应商，可发起支付。' }); }
function openPaymentStep() { document.getElementById('paymentStepCard').scrollIntoView({ behavior: 'smooth', block: 'center' }); setStatus('请选择支付通道并创建支付单'); }
async function markCurrentOrderPaid() { if (!currentOrderId) return setStatus('请先选择订单'); const res = await fetch(API + `/api/purchase/orders/${currentOrderId}/mark-paid`, { method: 'POST' }); const d = await res.json(); renderOrderDetail(d.order); loadOrders(); setStatus('已标记支付成功'); }
function resetOrderWizard() { currentOrderId = ''; document.getElementById('orderWorkflowCard').textContent = '先创建订单草稿，系统再引导你逐步确认商务节点。'; document.getElementById('orderDetail').textContent = '请选择一笔订单查看分阶段详情。'; document.getElementById('currentOrderBadge').textContent = '未选择'; }

async function loadPaymentChannels() {
    try {
        const res = await fetch(API + '/api/purchase/payment-channels');
        const d = await res.json();
        const channels = d.channels || [];
        const select = document.getElementById('payChannel');
        select.innerHTML = channels.map(c => `<option value="${c.channel_code}">${c.channel_name} · ${c.currency}</option>`).join('');
    } catch (e) {}
}

async function createOrderPayment() {
    if (!currentOrderId) return setStatus('请先选择订单');
    const payload = {
        order_id: currentOrderId,
        payment_channel: document.getElementById('payChannel').value,
        amount: parseFloat(document.getElementById('payAmount').value) || 0,
        currency: document.getElementById('payCurrency').value,
        subject: document.getElementById('paySubject').value
    };
    const res = await fetch(API + `/api/purchase/orders/${currentOrderId}/payments`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const d = await res.json();
    document.getElementById('paymentResult').innerHTML = `${escapeHtml(d.message || '已创建支付单')}${d.checkout_url ? ` <a href="${d.checkout_url}" target="_blank" class="underline text-[var(--accent-strong)]">打开支付链接</a>` : ''}`;
    await selectOrder(currentOrderId);
    setStatus('支付单已创建');
}

function openModal(id) { document.getElementById(id).classList.remove('hidden'); if (id === 'userModal') loadBindings(); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

function previewBinding() {
    const platform = document.getElementById('bPlatform').value;
    const name = document.getElementById('bName').value || '未填写';
    const country = document.getElementById('bCountry').value;
    const url = document.getElementById('bUrl').value || '未填写';
    document.getElementById('bindingPreview').innerHTML = `<div class="rounded-2xl border bg-white/80 p-4 space-y-2"><div><span class="text-[var(--muted)]">平台：</span>${escapeHtml(platform)}</div><div><span class="text-[var(--muted)]">店铺：</span>${escapeHtml(name)}</div><div><span class="text-[var(--muted)]">国家站点：</span>${escapeHtml(country)}</div><div><span class="text-[var(--muted)]">链接：</span>${escapeHtml(url)}</div></div>`;
}

async function loadBindings() {
    try {
        const res = await fetch(API + '/api/user/store-bindings'); const d = await res.json();
        const ss = d.stores || [];
        document.getElementById('storeList').innerHTML = ss.length ? ss.map(s => `<div class="soft-card p-4 rounded-[22px] border border-[rgba(32,25,19,.06)]"><div class="flex justify-between gap-3 items-start"><div><div class="font-semibold">${escapeHtml(s.store_name)}</div><div class="text-xs text-[var(--muted)] mt-1">${escapeHtml(s.platform)} · ${escapeHtml(s.country)}${s.store_url ? ` · <a href="${s.store_url}" target="_blank" class="underline">店铺链接</a>` : ''}</div></div><div class="flex gap-2"><span class="px-2 py-1 rounded-full bg-[rgba(47,93,80,.08)] text-[var(--forest)] text-xs">已绑定</span><button onclick="promptUnbind(${s.id}, '${esc(s.store_name)}', '${esc(s.platform)}')" class="action-btn">解绑</button></div></div><div class="mt-3 text-xs text-[var(--muted)]">该店铺可用于站点映射、订单归属、支付与履约流程关联。</div></div>`).join('') : '<span class="text-[var(--muted)]">暂无</span>';
    } catch (e) {}
}

async function bindStore() {
    try {
        await fetch(API + '/api/user/store-bindings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ platform: document.getElementById('bPlatform').value, store_name: document.getElementById('bName').value, store_url: document.getElementById('bUrl').value, access_token: document.getElementById('bToken').value, country: document.getElementById('bCountry').value }) });
        previewBinding();
        setStatus('绑定成功');
        loadBindings();
    } catch (e) { setStatus('绑定失败'); }
}

function promptUnbind(id, name, platform) {
    pendingUnbindId = id;
    document.getElementById('unbindText').innerHTML = `<div><span class="text-[var(--muted)]">店铺：</span>${escapeHtml(name)}</div><div class="mt-2"><span class="text-[var(--muted)]">平台：</span>${escapeHtml(platform)}</div><div class="mt-2">解绑后，该店铺对应的站点映射、上架归属与订单归因将中断。</div>`;
    openModal('unbindModal');
}

async function confirmUnbind() {
    if (!pendingUnbindId) return;
    try {
        await fetch(API + `/api/user/store-bindings/${pendingUnbindId}`, { method: 'DELETE' });
        pendingUnbindId = null;
        closeModal('unbindModal');
        loadBindings();
        setStatus('解绑成功');
    } catch (e) { setStatus('解绑失败'); }
}

function setStatus(msg) {
    const el = document.getElementById('statusText');
    if (!el) return;
    el.textContent = msg;
    setTimeout(() => {
        if (el) el.textContent = '系统就绪';
    }, 2500);
}


function bindListingEntryTrigger() {
    const btn = document.getElementById('chatListingEntryBtn');
    if (!btn) return;
    btn.addEventListener('click', () => openModal('listingModal'));
}

async function hydrateLocalChatsFromBackend() {
    try {
        const res = await fetch(API + '/api/chat/history?limit=200');
        if (!res.ok) return [];
        const data = await res.json();
        const messages = Array.isArray(data.messages) ? data.messages : [];
        const groups = new Map();
        for (const row of messages) {
            const sid = (row.session_id || '').trim();
            if (!sid) continue;
            if (!groups.has(sid)) {
                groups.set(sid, {
                    id: `chat_backend_${sid}`,
                    title: '历史会话',
                    created_at: row.created_at || new Date().toISOString(),
                    updated_at: row.created_at || new Date().toISOString(),
                    messages: [],
                    backend_session_id: sid,
                    source: 'backend',
                });
            }
            const session = groups.get(sid);
            session.messages.push({
                role: row.role === 'assistant' ? 'assistant' : 'user',
                content: row.content || '',
                ts: Date.parse(row.created_at || '') || Date.now(),
            });
            const created = row.created_at || session.created_at;
            if (!session.created_at || created < session.created_at) session.created_at = created;
            if (!session.updated_at || created > session.updated_at) session.updated_at = created;
        }
        for (const session of groups.values()) {
            const firstUser = session.messages.find(m => m.role === 'user' && m.content);
            session.title = (firstUser?.content || session.messages[0]?.content || '历史会话').slice(0, 18);
        }
        return [...groups.values()].sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
    } catch (e) {
        return [];
    }
}

function updateSidebarHistoryVisibility(page) {
    const section = document.getElementById('sidebarHistorySection');
    if (!section) return;
    section.classList.toggle('hidden', page !== 'chat');
}


async function initLocalChats() {
    try {
        localChatSessions = JSON.parse(localStorage.getItem('ta_chat_sessions') || '[]');
    } catch (e) {
        localChatSessions = [];
    }
    if (!Array.isArray(localChatSessions)) localChatSessions = [];
    if (!localChatSessions.length) {
        startNewChat();
    } else {
        activeSessionId = localChatSessions[0]?.id || '';
        if (!activeSessionId) {
            startNewChat();
        } else {
            renderLocalHistoryChips();
            restoreLocalSession(activeSessionId);
        }
    }
    saveLocalChats();
    renderLocalHistoryChips();
}



function snapshotActiveSessionFromUI() {
    if (!activeSessionId) return;
    const session = localChatSessions.find(s => s.id === activeSessionId);
    const box = document.getElementById('chatMessages');
    if (!session || !box) return;
    if (Array.isArray(session.messages) && session.messages.length) return;

    const rows = [...box.querySelectorAll('div.flex')];
    const parsed = [];
    rows.forEach(row => {
        const bubble = row.querySelector('.bubble-user, .bubble-ai');
        if (!bubble) return;
        const role = bubble.classList.contains('bubble-user') ? 'user' : 'assistant';
        const text = bubble.innerText?.trim();
        if (!text) return;
        parsed.push({ role, content: text, ts: Date.now() });
    });
    if (parsed.length) {
        session.messages = parsed;
        session.title = buildSessionTitle(session);
        session.updated_at = new Date().toISOString();
    }
}

function buildSessionTitle(session) {
    if (!session) return '新聊天';
    if (session.title && session.title !== '新聊天') return session.title;
    const msgs = Array.isArray(session.messages) ? session.messages : [];
    const firstUser = msgs.find(m => m.role === 'user' && String(m.content || '').trim());
    const firstAny = msgs.find(m => String(m.content || '').trim());
    return (firstUser?.content || firstAny?.content || '新聊天').slice(0, 18);
}

function finalizeActiveSessionBeforeSwitch() {
    if (!activeSessionId) return;
    const session = localChatSessions.find(s => s.id === activeSessionId);
    if (!session) return;
    session.title = buildSessionTitle(session);
    session.updated_at = session.updated_at || new Date().toISOString();
}

function startNewChat() {
    snapshotActiveSessionFromUI();
    finalizeActiveSessionBeforeSwitch();
    const id = `chat_${Date.now()}`;
    const now = new Date().toISOString();
    const item = { id, title: '新聊天', created_at: now, updated_at: now, messages: [], backend_session_id: '' };
    localChatSessions.unshift(item);
    localChatSessions = localChatSessions.slice(0, 20);
    activeSessionId = id;
    chatSession = '';
    const box = document.getElementById('chatMessages');
    if (box) box.innerHTML = `<div class="text-center text-[var(--muted)] py-16"><p class="serif-title text-4xl text-[var(--text)] mb-3">准备好了，随时开始</p><p class="text-sm">有问题，尽管问。</p></div>`;
    document.getElementById('chatInput').value = '';
    saveLocalChats();
    renderLocalHistoryChips();
    go('chat');
}

function persistChatMessage(role, content) {
    if (!activeSessionId) return;
    const session = localChatSessions.find(s => s.id === activeSessionId);
    if (!session) return;
    session.messages.push({ role, content, ts: Date.now() });
    session.updated_at = new Date().toISOString();
    if (role === 'assistant' && session.id !== activeSessionId) session.unread = (session.unread || 0) + 1;
    if (session.title === '新聊天' && role === 'user') {
        session.title = content.slice(0, 18) || '新聊天';
    }
    saveLocalChats();
    renderLocalHistoryChips();
}

function restoreLocalSession(sessionId) {
    const session = localChatSessions.find(s => s.id === sessionId);
    if (!session) return;
    session.unread = 0;
    chatSession = session.backend_session_id || '';
    const box = document.getElementById('chatMessages');
    if (!box) return;
    box.innerHTML = '';
    if (!session.messages.length) {
        box.innerHTML = `<div class="text-center text-[var(--muted)] py-16"><p class="serif-title text-4xl text-[var(--text)] mb-3">准备好了，随时开始</p><p class="text-sm">有问题，尽管问。</p></div>`;
        return;
    }
    session.messages.forEach(m => addMsg(m.role === 'user' ? 'user' : 'ai', m.content));
}

function renderLocalHistoryChips() {
    const el = document.getElementById('sidebarChatHistory');
    if (!el) return;
    if (!localChatSessions.length && activeSessionId) {
        const now = new Date().toISOString();
        localChatSessions = [{ id: activeSessionId, title: '新聊天', created_at: now, updated_at: now, messages: [], backend_session_id: '' }];
    }
    if (!localChatSessions.length) {
        el.innerHTML = '<span class="text-[var(--muted)] text-xs px-2">暂无历史会话</span>';
        return;
    }
    const sorted = [...localChatSessions].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0) || new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
    el.innerHTML = sorted.slice(0, 20).map(s => `
        <div class="chat-history-row ${s.id===activeSessionId ? 'active' : ''}">
            <button onclick="switchChatSession('${s.id}')" class="w-full text-left px-3 py-2.5">
                <div class="flex items-center gap-2 pr-1">
                    <div class="truncate text-xs font-semibold flex-1" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</div>
                    ${s.unread ? `<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500 text-white">${s.unread}</span>` : ''}
                </div>
                <div class="text-[10px] text-[var(--muted)] mt-1">${formatSessionTime(s.created_at)}</div>
            </button>
            <div class="history-actions-pop" role="tooltip">
                <button onclick="renameChatSession('${s.id}', event)" class="px-2 py-1 text-[10px] rounded-md bg-white border">重命名</button>
                <button onclick="togglePinSession('${s.id}', event)" class="px-2 py-1 text-[10px] rounded-md bg-white border">${s.pinned ? '取消置顶' : '置顶'}</button>
                <button onclick="deleteChatSession('${s.id}', event)" class="px-2 py-1 text-[10px] rounded-md bg-white border text-[var(--accent-strong)]">删除</button>
            </div>
        </div>
    `).join('');
}

function formatSessionTime(isoTime) {
    const d = new Date(isoTime || Date.now());
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

async function deleteChatSession(id, event) {
    if (event) event.stopPropagation();
    const idx = localChatSessions.findIndex(s => s.id === id);
    if (idx === -1) return;
    const deleting = localChatSessions[idx];
    if (deleting?.backend_session_id) {
        try {
            await fetch(API + `/api/chat/history/${encodeURIComponent(deleting.backend_session_id)}`, { method: 'DELETE' });
        } catch (e) {}
    }
    const wasActive = activeSessionId === id;
    localChatSessions.splice(idx, 1);

    if (!localChatSessions.length) {
        saveLocalChats();
        startNewChat();
        return;
    }

    if (wasActive) {
        activeSessionId = localChatSessions[0].id;
        restoreLocalSession(activeSessionId);
    }

    saveLocalChats();
    renderLocalHistoryChips();
}

function switchChatSession(id) {
    activeSessionId = id;
    restoreLocalSession(id);
    renderLocalHistoryChips();
    go('chat');
}

function saveLocalChats() {
    try {
        localStorage.setItem('ta_chat_sessions', JSON.stringify(localChatSessions));
    } catch (e) {}
}

function renameChatSession(id, event) {
    if (event) event.stopPropagation();
    const session = localChatSessions.find(s => s.id === id);
    if (!session) return;
    const next = window.prompt('重命名会话', session.title || '');
    if (!next || !next.trim()) return;
    session.title = next.trim().slice(0, 50);
    saveLocalChats();
    renderLocalHistoryChips();
}

function togglePinSession(id, event) {
    if (event) event.stopPropagation();
    const session = localChatSessions.find(s => s.id === id);
    if (!session) return;
    session.pinned = !session.pinned;
    saveLocalChats();
    renderLocalHistoryChips();
}

function openListingModal(prefill = {}) {
    openModal('listingModal');
    if (prefill.title) document.getElementById('listingTitle').value = prefill.title;
    if (prefill.price !== undefined) document.getElementById('listingPrice').value = prefill.price;
    if (prefill.category) document.getElementById('listingCategory').value = prefill.category;
    if (prefill.country && document.getElementById('listingCountry')) document.getElementById('listingCountry').value = prefill.country;
}

function openListingModalWithGuard() {
    openModal('listingModal');
}

async function generateListingAssets() {
    const out = document.getElementById('listingOut');
    const title = document.getElementById('listingTitle').value.trim();
    if (!title) {
        out.innerHTML = '<div class="text-red-500">请先填写商品标题。</div>';
        return;
    }
    out.innerHTML = '<div class="text-[var(--accent-strong)] text-sm">正在生成详情页与商品图，请稍候...</div>';

    const product = {
        title,
        price: parseFloat(document.getElementById('listingPrice').value) || 9.99,
        category: document.getElementById('listingCategory').value,
        description: document.getElementById('listingPrompt').value,
    };
    const country = document.getElementById('listingCountry').value;
    try {
        const [detailRes, imageRes] = await Promise.all([
            fetch(API + '/api/content/detail-page', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product, country }) }),
            fetch(API + '/api/content/image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product: { ...product, _image_provider: document.getElementById('listingProvider').value, _image_model: document.getElementById('listingModel').value, _aspect_ratio: document.getElementById('listingAspect').value }, style: document.getElementById('listingStyle').value, prompt: `${product.description || ''}；目标国家：${country}` }) })
        ]);
        const detail = await detailRes.json();
        const image = await imageRes.json();
        const detailTitle = detail.page?.page_title || '详情页已生成';
        const preview = detail.html_page?.preview_url ? `<a href="${detail.html_page.preview_url}" target="_blank" class="underline text-[var(--accent-strong)]">详情页预览</a>` : '无详情页预览链接';
        const imgPreview = image.preview_url ? `<a href="${image.preview_url}" target="_blank" class="underline text-[var(--forest)]">图片预览</a>` : '无图片预览链接';
        out.innerHTML = `<div class="space-y-3"><div class="text-lg font-semibold">${escapeHtml(title)}</div><div class="rounded-2xl border bg-white/80 p-3"><div class="font-semibold">商品详情页</div><div class="text-xs text-[var(--muted)] mt-1">${escapeHtml(detailTitle)}</div><div class="text-xs mt-2">${preview}</div></div><div class="rounded-2xl border bg-white/80 p-3"><div class="font-semibold">商品图</div><div class="text-xs text-[var(--muted)] mt-1">${escapeHtml(image.message || image.job_id || '图像任务已提交')}</div><div class="text-xs mt-2">${imgPreview}</div></div></div>`;
        addMsg('ai', `「${title}」商品上架内容已生成：详情页与商品图已准备完成。`);
        persistChatMessage('assistant', `「${title}」商品上架内容已生成`);
        go('chat');
    } catch (e) {
        out.innerHTML = `<div class="text-red-500 text-sm">生成失败：${escapeHtml(e.message)}</div>`;
    }
}

async function loadSkills() {
    const box = document.getElementById('skillsList');
    if (!box) return;
    try {
        const res = await fetch(API + '/api/skills');
        const d = await res.json();
        const skills = d.skills || [];
        box.innerHTML = skills.length ? skills.map(s => `<div class="rounded-xl border bg-white/70 p-2"><div class="font-semibold text-[12px]">${escapeHtml(s.name)}</div><div class="text-[11px] mt-1">${escapeHtml((s.scripts || []).join(', ') || 'script 待补充')}</div></div>`).join('') : '暂无技能';
    } catch (e) {
        box.innerHTML = '技能加载失败';
    }
}


function toggleQuickTools() {
    const menu = document.getElementById('quickToolsMenu');
    if (!menu) return;
    menu.classList.toggle('hidden');
}

function bindQuickAction(action) {
    const menu = document.getElementById('quickToolsMenu');
    if (menu) menu.classList.add('hidden');
    if (action === 'upload') {
        document.getElementById('chatImage')?.click();
    }
}

function bindOutsideClickForTools() {
    document.addEventListener('click', (event) => {
        const menu = document.getElementById('quickToolsMenu');
        if (!menu || menu.classList.contains('hidden')) return;
        const trigger = event.target.closest('button');
        if (event.target.closest('#quickToolsMenu')) return;
        if (trigger && trigger.getAttribute('onclick') === 'toggleQuickTools()') return;
        menu.classList.add('hidden');
    });
}
