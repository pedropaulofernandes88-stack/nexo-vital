(() => {
  'use strict';

  const state = { data: null, geo: null, countries: [], filtered: [], charts: {}, selected: null };
  const $ = (selector) => document.querySelector(selector);
  const fmt = new Intl.NumberFormat('pt-BR');
  const one = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const two = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const pct = (value, digits = 1) => `${(100 * value).toFixed(digits).replace('.', ',')}%`;
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const palette = { below: '#f06c51', within: '#aab5b2', above: '#16b8ae', blue: '#4d8bd8', lime: '#b8d552' };
  const positionLabel = { below: 'abaixo da banda', within: 'dentro da banda', above: 'acima da banda' };
  const featureLabel = {
    under5_mortality: 'Mortalidade até 5 anos', obesity_prevalence: 'Obesidade',
    gdp_per_capita_ppp: 'PIB per capita PPP', health_spending_ppp: 'Gasto em saúde PPP',
    tobacco_prevalence: 'Uso de tabaco'
  };

  function chartDefaults() {
    Chart.defaults.font.family = 'Inter';
    Chart.defaults.color = css('--muted');
    Chart.defaults.borderColor = css('--line');
    Chart.defaults.animation.duration = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 500;
  }

  async function boot() {
    try {
      const [data, geo] = await Promise.all([
        fetch('data/observatory.json').then(checkResponse).then(r => r.json()),
        fetch('data/world.geo.json').then(checkResponse).then(r => r.json())
      ]);
      state.data = data; state.geo = geo; state.countries = data.model.countries; state.filtered = state.countries;
      chartDefaults(); bindControls(); populateFilters(); renderAll();
    } catch (error) {
      console.error(error);
      document.body.insertAdjacentHTML('afterbegin', '<div class="load-error">Não foi possível carregar os artefatos. Execute o dashboard por um servidor HTTP local.</div>');
    }
  }

  function checkResponse(response) { if (!response.ok) throw new Error(`${response.status} ${response.url}`); return response; }
  function setText(selector, value) { const element = $(selector); if (element) element.textContent = value; }

  function bindControls() {
    $('#region-filter').addEventListener('change', applyFilters);
    $('#position-filter').addEventListener('change', applyFilters);
    $('#country-search').addEventListener('input', applyFilters);
    $('#oecd-class').addEventListener('change', renderOecd);
    $('#theme-toggle').addEventListener('click', () => {
      const dark = document.documentElement.dataset.theme === 'dark';
      document.documentElement.dataset.theme = dark ? '' : 'dark';
      localStorage.setItem('nexo-theme', dark ? 'light' : 'dark');
      chartDefaults(); renderCharts();
    });
    if (localStorage.getItem('nexo-theme') === 'dark') document.documentElement.dataset.theme = 'dark';
  }

  function populateFilters() {
    const regions = [...new Set(state.countries.map(d => d.region))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
    regions.forEach(region => $('#region-filter').append(new Option(region, region)));
    const classes = [...new Map(state.data.medicines.oecd_latest.map(d => [d.class_id, d.class_name])).entries()];
    classes.forEach(([id, name]) => $('#oecd-class').append(new Option(name, id)));
    $('#oecd-class').value = 'antidepressants';
  }

  function renderAll() {
    renderHeadline(); renderMap(); renderCountry(state.countries.find(d => d.country_iso3 === 'BRA') || state.countries[0]);
    renderCharts(); renderModelText(); renderMedicinesText(); renderBrazilText();
  }

  function renderHeadline() {
    const c = state.data.coverage;
    setText('#metric-countries', fmt.format(c.countries)); setText('#metric-observations', fmt.format(c.rows));
    setText('#metric-medicine', fmt.format(state.data.medicines.glass_summary.countries));
    setText('#filter-count', `${state.filtered.length} países`);
  }

  function applyFilters() {
    const region = $('#region-filter').value, position = $('#position-filter').value;
    const search = $('#country-search').value.trim().toLocaleLowerCase('pt-BR');
    state.filtered = state.countries.filter(d => (region === 'all' || d.region === region) &&
      (position === 'all' || d.position === position) && (!search || d.country_name.toLocaleLowerCase('pt-BR').includes(search)));
    setText('#filter-count', `${state.filtered.length} países`);
    updateMapFilter(); renderAtlasCharts();
    if (state.filtered.length === 1) renderCountry(state.filtered[0]);
  }

  function residualColor(value) {
    if (value == null) return css('--line');
    const scale = d3.scaleLinear().domain([-10, 0, 10]).range([palette.below, '#c8cfcc', palette.above]).clamp(true);
    return scale(value);
  }

  function renderMap() {
    const host = d3.select('#world-map'); host.selectAll('*').remove();
    const width = 1000, height = 510, byIso = new Map(state.countries.map(d => [d.country_iso3, d]));
    const svg = host.append('svg').attr('viewBox', `0 0 ${width} ${height}`).attr('aria-hidden', 'true');
    const projection = d3.geoNaturalEarth1().fitExtent([[6, 6], [width - 6, height - 6]], state.geo);
    const path = d3.geoPath(projection);
    svg.selectAll('path').data(state.geo.features).join('path')
      .attr('class', 'country-path').attr('data-iso', d => d.id).attr('d', path)
      .attr('fill', d => residualColor(byIso.get(d.id)?.residual_loo))
      .attr('tabindex', d => byIso.has(d.id) ? 0 : null).attr('role', d => byIso.has(d.id) ? 'button' : null)
      .attr('aria-label', d => byIso.has(d.id) ? `${byIso.get(d.id).country_name}: desvio ${one.format(byIso.get(d.id).residual_loo)} anos` : null)
      .on('mouseenter focus', (event, d) => showTooltip(event, byIso.get(d.id)))
      .on('mouseleave blur', hideTooltip)
      .on('click keydown', (event, d) => { if (event.type === 'click' || event.key === 'Enter') { const country = byIso.get(d.id); if (country) renderCountry(country); } });
    updateMapFilter();
  }

  function updateMapFilter() {
    const visible = new Set(state.filtered.map(d => d.country_iso3));
    d3.selectAll('.country-path').classed('filtered', function() { const iso = this.dataset.iso; return state.countries.some(d => d.country_iso3 === iso) && !visible.has(iso); });
  }

  function showTooltip(event, country) {
    if (!country) return; const tip = $('#tooltip');
    tip.innerHTML = `<strong>${escapeHtml(country.country_name)}</strong><br>${one.format(country.residual_loo)} anos · ${positionLabel[country.position]}`;
    tip.style.display = 'block'; tip.style.left = `${Math.min(innerWidth - 270, event.clientX + 12)}px`; tip.style.top = `${Math.max(8, event.clientY - 38)}px`; tip.setAttribute('aria-hidden', 'false');
  }
  function hideTooltip() { const tip = $('#tooltip'); tip.style.display = 'none'; tip.setAttribute('aria-hidden', 'true'); }
  function escapeHtml(value) { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; }

  function renderCountry(country) {
    state.selected = country; d3.selectAll('.country-path').classed('selected', function() { return this.dataset.iso === country.country_iso3; });
    setText('#country-name', country.country_name); setText('#country-context', `${country.region} · ${country.income_group} · ${positionLabel[country.position]}`);
    setText('#country-observed', `${one.format(country.life_expectancy)} anos`);
    setText('#country-predicted', `${one.format(country.predicted_life_expectancy_loo)} anos`);
    setText('#country-residual', `${country.residual_loo > 0 ? '+' : ''}${one.format(country.residual_loo)} anos`);
    setText('#country-stability', country.stable_all_specs ? 'alta' : 'sensível');
    const factors = [
      ['PIB PPP', `$ ${fmt.format(Math.round(country.gdp_per_capita_ppp))}`],
      ['Gasto em saúde PPP', `$ ${fmt.format(Math.round(country.health_spending_ppp))}`],
      ['Mortalidade <5', `${one.format(country.under5_mortality)} / 1.000`],
      ['Obesidade', `${one.format(country.obesity_prevalence)}%`], ['Tabaco', `${one.format(country.tobacco_prevalence)}%`]
    ];
    const host = $('#country-factors'); host.replaceChildren(...factors.map(([name, value]) => {
      const row = document.createElement('div'); row.className = 'factor';
      const label = document.createElement('span'), datum = document.createElement('span'); label.textContent = name; datum.textContent = value; row.append(label, datum); return row;
    }));
  }

  function chart(id, config) { if (state.charts[id]) state.charts[id].destroy(); state.charts[id] = new Chart($(id), config); }
  function baseOptions(extra = {}) { return { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: 'nearest' }, plugins: { legend: { display: false }, tooltip: { padding: 10 } }, scales: { x: { grid: { color: css('--line') } }, y: { grid: { color: css('--line') } } }, ...extra }; }
  function renderCharts() { renderAtlasCharts(); renderModelCharts(); renderMedicineCharts(); renderOecd(); renderBrazilCharts(); }

  function renderAtlasCharts() {
    const data = state.filtered;
    chart('#expected-chart', { type: 'scatter', data: { datasets: ['below','within','above'].map(position => ({ label: positionLabel[position], data: data.filter(d => d.position === position).map(d => ({ x: d.predicted_life_expectancy_loo, y: d.life_expectancy, country: d.country_name })), backgroundColor: palette[position], pointRadius: 4 })) }, options: baseOptions({ plugins: { legend: { display: true, labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: c => `${c.raw.country}: previsto ${one.format(c.raw.x)}, observado ${one.format(c.raw.y)}` } } }, scales: { x: { title: { display: true, text: 'Previsto LOO (anos)' } }, y: { title: { display: true, text: 'Observado (anos)' } } } }) });
    const extremes = [...data].sort((a,b) => a.residual_loo - b.residual_loo); const ranked = [...extremes.slice(0, 8), ...extremes.slice(-8)].sort((a,b) => a.residual_loo - b.residual_loo);
    chart('#residual-chart', { type: 'bar', data: { labels: ranked.map(d => d.country_name), datasets: [{ data: ranked.map(d => d.residual_loo), backgroundColor: ranked.map(d => palette[d.position]), borderRadius: 4 }] }, options: baseOptions({ indexAxis: 'y', scales: { x: { title: { display: true, text: 'resíduo (anos)' } }, y: { grid: { display: false } } } }) });
  }

  function renderModelText() {
    const m = state.data.model.metrics, stable = state.data.model.sensitivity.find(d => d.specification === 'main')?.stable_countries;
    setText('#model-r2', two.format(m.loo_predictive_r_squared)); setText('#model-rmse', one.format(m.loo_rmse_years));
    setText('#model-band', `± ${one.format(m.conformal_radius_years)}`); setText('#model-stable', `${stable}/${m.n_countries}`);
    const c = state.data.model.concentration;
    setText('#concentration-title', `${c.observed_in_region} dos ${c.below_countries} países abaixo estão na África Subsaariana.`);
    setText('#concentration-copy', `Sob seleção aleatória, seriam esperados ${one.format(c.expected_in_region)}. A sobrerrepresentação é ${two.format(c.enrichment_ratio)} vezes o esperado.`);
    setText('#concentration-observed', c.observed_in_region); setText('#concentration-expected', one.format(c.expected_in_region)); setText('#concentration-p', c.hypergeometric_one_sided_p_value.toLocaleString('pt-BR', { maximumSignificantDigits: 3 }));
  }

  const ciPlugin = { id: 'confidenceIntervals', afterDatasetsDraw(chartInstance, args, options) { if (!options?.values) return; const { ctx, scales: { x, y } } = chartInstance; ctx.save(); ctx.strokeStyle = css('--ink'); ctx.lineWidth = 1.5; options.values.forEach((item, index) => { const yy = y.getPixelForValue(index), x1 = x.getPixelForValue(item.low), x2 = x.getPixelForValue(item.high); ctx.beginPath(); ctx.moveTo(x1, yy); ctx.lineTo(x2, yy); ctx.moveTo(x1, yy - 4); ctx.lineTo(x1, yy + 4); ctx.moveTo(x2, yy - 4); ctx.lineTo(x2, yy + 4); ctx.stroke(); }); ctx.restore(); } };
  Chart.register(ciPlugin);

  function renderModelCharts() {
    const coefficients = state.data.model.coefficients.filter(d => d.term !== 'intercept');
    chart('#coefficient-chart', { type: 'bar', data: { labels: coefficients.map(d => featureLabel[d.term] || d.term), datasets: [{ data: coefficients.map(d => d.estimate), backgroundColor: coefficients.map(d => d.estimate >= 0 ? palette.above : palette.below), borderRadius: 4, barThickness: 14 }] }, options: baseOptions({ indexAxis: 'y', plugins: { legend: { display: false }, confidenceIntervals: { values: coefficients.map(d => ({ low: d.ci95_low, high: d.ci95_high })) }, tooltip: { callbacks: { afterLabel: c => `IC95% ${two.format(coefficients[c.dataIndex].ci95_low)} a ${two.format(coefficients[c.dataIndex].ci95_high)}` } } }, scales: { x: { title: { display: true, text: 'anos por 1 desvio-padrão' } }, y: { grid: { display: false } } } }) });
    const countries = state.data.model.countries;
    chart('#pca-chart', { type: 'scatter', data: { datasets: [1,2].map(k => ({ label: `Perfil ${k}`, data: countries.filter(d => d.cluster_k2 === k).map(d => ({ x: d.pc1, y: d.pc2, country: d.country_name })), backgroundColor: k === 1 ? palette.above : palette.below, pointRadius: 4 })) }, options: baseOptions({ plugins: { legend: { display: true, labels: { usePointStyle: true } }, tooltip: { callbacks: { label: c => c.raw.country } } }, scales: { x: { title: { display: true, text: 'PC1' } }, y: { title: { display: true, text: 'PC2' } } } }) });
    const selection = state.data.segmentation.cluster_selection, stability = new Map(state.data.segmentation.bootstrap_stability.map(d => [d.k, d.mean]));
    chart('#cluster-chart', { type: 'line', data: { labels: selection.map(d => d.k), datasets: [{ label: 'Silhouette', data: selection.map(d => d.silhouette), borderColor: palette.blue, backgroundColor: palette.blue, tension: .25 }, { label: 'Estabilidade ARI', data: selection.map(d => stability.get(d.k) ?? null), borderColor: palette.lime, backgroundColor: palette.lime, spanGaps: false }] }, options: baseOptions({ plugins: { legend: { display: true, labels: { usePointStyle: true } } }, scales: { x: { title: { display: true, text: 'Número de grupos (k)' } }, y: { min: 0, max: 1 } } }) });
  }

  function renderMedicinesText() {
    const s = state.data.medicines.glass_summary; setText('#antibiotic-ratio', `${one.format(s.max_min_ratio)}×`);
    setText('#access-target', s.countries_meeting_access_70); setText('#coverage-caveats', `${s.countries_with_coverage_caveat} países`);
  }

  function renderMedicineCharts() {
    const latest = state.data.medicines.glass_latest;
    chart('#antibiotic-chart', { type: 'scatter', data: { datasets: [{ data: latest.map(d => ({ x: d.total_ddd_per_1000_day, y: d.access_share_pct, country: d.country_name, caveat: d.has_coverage_caveat, year: d.year })), backgroundColor: latest.map(d => d.has_coverage_caveat ? palette.coral : palette.cyan), pointRadius: latest.map(d => d.has_coverage_caveat ? 6 : 4) }] }, options: baseOptions({ plugins: { tooltip: { callbacks: { label: c => `${c.raw.country} (${c.raw.year}): ${one.format(c.raw.x)} DDD; Access ${one.format(c.raw.y)}%`, afterLabel: c => c.raw.caveat ? 'Cobertura com ressalva' : 'Sem ressalva específica' } } }, scales: { x: { title: { display: true, text: 'DDD / 1.000 habitantes / dia' } }, y: { min: 0, max: 100, title: { display: true, text: 'Participação Access (%)' } } } }) });
    const sorted = [...latest].sort((a,b) => b.total_ddd_per_1000_day - a.total_ddd_per_1000_day); const ranks = [...sorted.slice(0, 8), ...sorted.slice(-8).reverse()];
    chart('#antibiotic-ranking', { type: 'bar', data: { labels: ranks.map(d => `${d.country_name} · ${d.year}`), datasets: [{ data: ranks.map(d => d.total_ddd_per_1000_day), backgroundColor: ranks.map(d => d.has_coverage_caveat ? palette.coral : palette.blue), borderRadius: 3 }] }, options: baseOptions({ indexAxis: 'y', scales: { x: { title: { display: true, text: 'DDD / 1.000 / dia' } }, y: { grid: { display: false } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { afterLabel: c => ranks[c.dataIndex].coverage_caveat || 'Sem ressalva específica no conjunto' } } } }) });
  }

  function renderOecd() {
    const classId = $('#oecd-class').value || 'antidepressants'; const rows = state.data.medicines.oecd_change.filter(d => d.class_id === classId).sort((a,b) => b.percent_change - a.percent_change);
    chart('#oecd-chart', { type: 'bar', data: { labels: rows.map(d => d.country_iso3), datasets: [{ data: rows.map(d => d.percent_change), backgroundColor: rows.map(d => d.percent_change >= 0 ? palette.cyan : palette.coral), borderRadius: 3 }] }, options: baseOptions({ scales: { x: { grid: { display: false }, ticks: { maxRotation: 90, minRotation: 90 } }, y: { title: { display: true, text: 'mudança 2011–2021 (%)' } } } }) });
    const mean = rows[0]?.mean ?? 0, median = rows[0]?.median ?? 0, host = $('#oecd-insight'); host.replaceChildren();
    const strong = document.createElement('strong'), copy = document.createElement('p'), note = document.createElement('p'); strong.textContent = `${mean >= 0 ? '+' : ''}${one.format(mean)}%`; copy.textContent = 'mudança média entre os pares país-classe observados nos dois anos.'; note.textContent = `Mediana: ${one.format(median)}%. Diferenças de cobertura e dispensação limitam comparações.`; host.append(strong, copy, note);
  }

  function renderBrazilText() {
    const tourism = state.data.brazil.health_tourism, last = tourism.find(d => d.year === 2019) || tourism.at(-1), total = state.data.brazil.foreign_nationality_sus.find(d => d.nationality.startsWith('Todas'));
    setText('#tourism-2019', fmt.format(last.estimated_health_reason_arrivals)); setText('#sus-total', fmt.format(total.hospitalizations));
  }

  function renderBrazilCharts() {
    const tourism = state.data.brazil.health_tourism;
    chart('#tourism-chart', { type: 'line', data: { labels: tourism.map(d => d.year), datasets: [{ data: tourism.map(d => d.estimated_health_reason_arrivals), borderColor: palette.cyan, backgroundColor: `${palette.cyan}30`, fill: true, tension: .3, pointRadius: 3 }] }, options: baseOptions({ scales: { x: { grid: { display: false } }, y: { ticks: { callback: v => `${Math.round(v/1000)} mil` } } } }) });
    const sus = state.data.brazil.foreign_nationality_sus.filter(d => !d.nationality.startsWith('Todas')).sort((a,b) => b.hospitalizations - a.hospitalizations).slice(0, 8);
    chart('#sus-chart', { type: 'bar', data: { labels: sus.map(d => d.nationality), datasets: [{ data: sus.map(d => d.hospitalizations), backgroundColor: palette.coral, borderRadius: 3 }] }, options: baseOptions({ indexAxis: 'y', scales: { x: { grid: { display: false } }, y: { grid: { display: false } } } }) });
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
