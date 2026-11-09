// Render with textContent: page-provided account names are data.
async function refresh() {
  const result=await chrome.runtime.sendMessage({command:'sites',arguments:{command:'list'}});
  document.querySelector('#entries').textContent=JSON.stringify(result || {unavailable:'Use sudo aresos admin chrome sites to inspect entries.'},null,2);
}
refresh();
