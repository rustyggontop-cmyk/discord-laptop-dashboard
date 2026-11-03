const $ = id => document.getElementById(id);
const set = (id, value) => $(id).textContent = value;
const setBar = (id, value) => $(id).style.width = `${Math.min(100, value)}%`;

async function refresh() {
  try {
    const s = await (await fetch('/api/status', {cache: 'no-store'})).json();
    set('host', s.host); set('os', `${s.os} · ${s.kernel}`); set('cpu', `${s.cpu}%`); setBar('cpu-bar', s.cpu);
    set('cores', `${s.cores} logical cores · load ${s.load.join(', ')}`);
    set('memory', `${s.memory.percent}%`); setBar('memory-bar', s.memory.percent); set('memory-detail', `${s.memory.used} / ${s.memory.total}`);
    set('disk', `${s.disk.percent}%`); setBar('disk-bar', s.disk.percent); set('disk-detail', `${s.disk.used} / ${s.disk.total}`);
    set('uptime', s.uptime); const bot = $('bot'); bot.textContent = s.bot_online ? 'Running' : 'Offline'; bot.className = s.bot_online ? 'good' : 'bad';
    set('battery', s.battery.available ? `${s.battery.percent}% · ${s.battery.charging ? 'Charging' : 'On battery'}` : 'Not detected');
    set('updated', `Updated ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`);
  } catch { set('updated', 'Status refresh failed'); }
}
refresh(); setInterval(refresh, 5000);

let pendingAction;
const dialog = $('confirm-dialog');
document.querySelectorAll('[data-action]').forEach(button => button.onclick = () => {
  pendingAction = button.dataset.action; const reboot = pendingAction === 'reboot';
  set('modal-title', reboot ? 'Restart laptop?' : 'Shut down laptop?');
  set('modal-copy', `Type ${pendingAction} to confirm this action.`); $('confirmation').value = ''; $('confirmation').placeholder = pendingAction; dialog.showModal();
});
$('confirm-button').onclick = async event => {
  event.preventDefault(); if ($('confirmation').value !== pendingAction) { $('confirmation').focus(); return; }
  $('confirm-button').disabled = true;
  const r = await fetch(`/api/power/${pendingAction}`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':window.CSRF_TOKEN}, body:JSON.stringify({confirm:pendingAction})});
  $('confirm-button').disabled = false; if (r.ok) { dialog.close(); set('updated', `Command sent: ${pendingAction}`); } else { set('modal-copy', 'Could not send action. Check server permissions.'); }
};
$('logout').onclick = async () => { await fetch('/logout', {method:'POST', headers:{'X-CSRF-Token':window.CSRF_TOKEN}}); location.href='/login'; };

