// Brief 28, group 16: the efficiency fixtures, served by fixture.mjs as
// /?case=efficiency-<name>. Invented content only. F1 to F4 give the node lists
// of control/chrome_tests/view_fixtures.py; F5 and F7 are for brief 28a's rows.
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const titled=title=>'document.title='+JSON.stringify(title)+';';

// F1: brief 20's long page, the same text as ci/fixture.mjs's matrix mode
// "long" (120 paragraphs, 80 labelled fields with values).
export const f1Body=()=>Array.from({length:120},(_,index)=>'<p>Paragraph '+index+' '+('readable article text '.repeat(20))+'</p>').join('')
  +'<form>'+Array.from({length:80},(_,index)=>'<label>Field '+index+'<input name="field'+index+'" value="Synthetic value '+index+'"></label>').join('')+'</form>';

// F2: 200 rows of 6 cells of exactly 12 letters and digits under a header row,
// and a small second table with a link and a checkbox in each row.
export const F2_ROWS=200,F2_COLUMNS=6;
export const f2Cell=(row,column)=>'r'+String(row).padStart(3,'0')+'c'+column+'abcdef';
export const f2Header=column=>'Column'+String(column).padStart(2,'0')+'name';
function f2Body(){
  const header='<tr>'+Array.from({length:F2_COLUMNS},(_,column)=>'<th>'+f2Header(column)+'</th>').join('')+'</tr>';
  const rows=Array.from({length:F2_ROWS},(_,row)=>'<tr>'+Array.from({length:F2_COLUMNS},(_,column)=>'<td>'+f2Cell(row,column)+'</td>').join('')+'</tr>').join('');
  const orders=Array.from({length:3},(_,row)=>'<tr><td>Order '+row+'</td><td><a href="/order/'+row+'">Open</a></td><td><input type="checkbox" aria-label="Select order '+row+'"></td></tr>').join('');
  return '<h1>Stock</h1><table aria-label="Stock">'+header+rows+'</table><table aria-label="Orders">'+orders+'</table>';
}

// F3: 300 links in a list between a navigation and a footer link group; one
// link's name is contained in no other link's name.
export const F3_UNIQUE='Quarterly zebra report',F3_UNIQUE_INDEX=217;
export const f3Name=index=>index===F3_UNIQUE_INDEX?F3_UNIQUE:'Result '+index+' of the listing';
function f3Body(){
  const nav='<nav aria-label="Site">'+Array.from({length:6},(_,index)=>'<a href="/section/'+index+'">Section '+index+'</a>').join('')+'</nav>';
  const list='<ul aria-label="Results">'+Array.from({length:300},(_,index)=>'<li><a href="/result/'+index+'">'+f3Name(index)+'</a></li>').join('')+'</ul>';
  const footer='<footer>'+Array.from({length:5},(_,index)=>'<a href="/footer/'+index+'">Footer '+index+'</a>').join('')+'</footer>';
  return nav+'<main><h1>Results</h1>'+list+'</main>'+footer;
}

// F4: a form of 25 fields. The task fills the six lines F4_FILLED and presses
// Save, which brief 20 refuses (efficiency-probe.mjs); a submission would reach
// the receiver under the run's id.
export const F4_FILLED=['Line 0','Line 1','Line 2','Line 3','Line 4','Line 5'];
function f4Body(id){
  const lines=Array.from({length:10},(_,index)=>'<label>Line '+index+' <input name="line'+index+'" value="Value '+index+'"></label>').join('');
  const countries=Array.from({length:200},(_,index)=>'<option value="c'+index+'"'+(index===7?' selected':'')+'>Country '+index+'</option>').join('');
  return '<form aria-label="Account" method="post" novalidate action="/receive?case=efficiency-f4-'+encodeURIComponent(id)+'">'
    +'<input type="hidden" name="csrf" value="fixture-csrf"><input type="hidden" name="step" value="2"><input type="hidden" name="cart" value="fixture-cart">'
    +lines+'<label>Born <input type="date" name="born" value="2001-02-03"></label>'
    +'<label><input type="checkbox" name="news" checked> News</label><label><input type="checkbox" name="offers"> Offers</label>'
    +'<fieldset role="radiogroup" aria-label="Plan"><label><input type="radio" name="plan" value="free" checked> Free</label><label><input type="radio" name="plan" value="paid"> Paid</label></fieldset>'
    +'<label>Country <select name="country">'+countries+'</select></label>'
    +'<label>Size <select name="size"><option>S</option><option selected>M</option><option>L</option></select></label>'
    +'<label>Email <input type="email" name="email" value="not-an-address" required aria-invalid="true" aria-describedby="email-error"></label><span id="email-error">Enter a valid address</span>'
    +'<label>Password <input type="password" name="password"></label>'
    +'<label>One-time code <input name="one_time" autocomplete="one-time-code"></label>'
    +'<label>Code <input name="code_text" value="Value code"></label><label>Nickname <input name="nickname"></label>'
    +'<label>Age <input type="number" name="age" value="30"></label><label>Volume <input type="range" name="volume" value="40"></label>'
    +'<label>Find <input type="search" name="find"></label><label><input type="checkbox" role="switch" name="dark"> Dark</label>'
    +'<button type="submit">Save</button></form>';
}

// F5: a free click that changes part of the page (5 rows replaced, the status
// line, one heading renamed, one paragraph removed: 8 changed lines), and with
// mode=load a page whose click loads a new document.
export const F5_ROWS=8;
function f5(mode){
  if(mode==='load')return {body:'<h1>Loader</h1><a href="/?case=efficiency-f5&amp;mode=loaded">Load the next document</a>',script:titled('Loader')};
  if(mode==='loaded')return {body:'<h1>Loaded document</h1><p>The next document loaded.</p>',script:titled('Loaded')};
  const rows=Array.from({length:F5_ROWS},(_,index)=>'<li>Row '+index+': pending item '+index+'</li>').join('');
  return {body:'<h1 id="summary">Queue summary</h1><p id="tip">Tip: rows refresh on request</p><ul aria-label="Rows">'+rows+'</ul><p role="status">Showing 8 rows, never refreshed</p><button type="button" id="refresh">Refresh rows</button>',
    script:titled('Queue')+"document.querySelector('#refresh').onclick=()=>{const rows=document.querySelectorAll('li');for(let index=0;index<5;index++)rows[index].textContent='Row '+index+': refreshed item '+index;document.querySelector('[role=status]').textContent='Showing 8 rows, refreshed once';document.querySelector('#summary').textContent='Queue summary, updated';document.querySelector('#tip').remove();};"};
}

// F7: result pages, each with a title of its own and a link to the next.
function f7(page){
  const results=Array.from({length:3},(_,index)=>'<li>Result '+page+'.'+(index+1)+' of the search</li>').join('');
  return {body:'<h1>Results page '+page+'</h1><ul aria-label="Results">'+results+'</ul><a href="/?case=efficiency-f7&amp;page='+(page+1)+'">Next page</a>',script:titled('Results page '+page)};
}

// The pages of "list 25 open tabs": titles of about 30 characters.
export const tabTitle=id=>'Efficiency fixture tab no. '+String(id).padStart(2,'0');

export function efficiencyPage(url){
  const name=url.searchParams.get('case').slice('efficiency-'.length);
  const page=Math.max(1,Math.min(99,Number.parseInt(url.searchParams.get('page')||'1',10)||1));
  const id=String(url.searchParams.get('id')||'fixture').slice(0,40);
  if(name==='f1')return {body:f1Body(),script:titled('Long')};
  if(name==='f2')return {body:f2Body(),script:titled('Table')};
  if(name==='f3')return {body:f3Body(),script:titled('Listing')};
  if(name==='f4')return {body:f4Body(id),script:titled('Form')};
  if(name==='f5')return f5(url.searchParams.get('mode'));
  if(name==='f7')return f7(page);
  if(name==='tab')return {body:'<p>'+escape(tabTitle(id))+'</p>',script:titled(tabTitle(id))};
  return null;
}
