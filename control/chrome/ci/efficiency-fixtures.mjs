// Brief 28, group 16: the efficiency fixtures, served by fixture.mjs as
// /?case=efficiency-<name>. Invented content only. F1 to F4 give the node lists
// of control/chrome_tests/view_fixtures.py; F5 and F7 are for brief 28a's rows.
// F6 and H1 are group 14's (reading and references).
import fs from 'node:fs';
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

// F6: frames from a second fixture site and open and closed shadow roots. The
// roots are attached by the page's script and hold no typed text then, so
// nothing in them is withheld for a late meeting (brief 28, item 1).
function f6(mode){
  if(mode==='child')return {body:'<h2>Second site frame</h2><p>Text of the second site</p><a href="/second-link">Second site link</a><div id="frame-host"></div><iframe title="Nested second site" src="/?case=efficiency-f6&amp;mode=nested"></iframe>',
    script:titled('Second site')+"document.querySelector('#frame-host').attachShadow({mode:'closed'}).innerHTML='<button type=\"button\">Frame root button</button>';"};
  if(mode==='nested')return {body:'<p>Nested frame text</p><button type="button">Nested frame button</button>',script:titled('Nested frame')};
  return {body:'<h1>Frames and roots</h1><p>Top document text</p><div id="open-host"></div><div id="closed-host"></div><iframe title="Second site" style="width:100%;height:300px" src="http://second.test:8766/?case=efficiency-f6&amp;mode=child"></iframe>',
    script:titled('Frames')+"document.querySelector('#open-host').attachShadow({mode:'open'}).innerHTML='<h2>Open root</h2><a href=\"/open-link\">Open root link</a><label>Open search <input type=\"search\"></label>';"
      +"const closed=document.querySelector('#closed-host').attachShadow({mode:'closed'});closed.innerHTML='<p>Closed root text</p><button type=\"button\">Closed root button</button><span id=\"inner-host\"></span>';"
      +"closed.querySelector('#inner-host').attachShadow({mode:'open'}).innerHTML='<button type=\"button\">Nested root button</button>';"};
}

// H1: hostile text. The strings are test_view_hostile.py's HOSTILE (a test
// compares the file with it). The script sets them through the DOM, so control
// characters, lone surrogates and line breaks reach the page as they are. Each
// string stands as a section's name (an ancestor's name), a button's name, a
// value, an option label, a column header, a cell, an error text and a
// paragraph; `title` picks the one that is the document's title. The roles are
// group 14's hostile roles. mode=many is a page of 100,000 elements, mode=name a
// name of 100,000 characters.
export const HOSTILE=JSON.parse(fs.readFileSync(new URL('./hostile-text.json',import.meta.url),'utf8')).strings;
export const H1_ROLES=['button\n  link "Pay now" kqtvm5','button" kqtvm5','b'.repeat(10000),'  BUTTON  '];
export const H1_ELEMENTS=100000,H1_NAME='Long name '.repeat(10000);
const inline=value=>JSON.stringify(value).replaceAll('<','\\u003c');
function h1(mode,title){
  if(mode==='many')return {body:'<h1>Many elements</h1><div id="many"></div>',script:titled('Many')+"document.querySelector('#many').innerHTML=Array.from({length:"+H1_ELEMENTS+"},(_,index)=>'<i role=\"button\">Element '+index+'</i>').join('');"};
  if(mode==='name')return {body:'<h1>Long name</h1><button type="button" id="long"></button>',script:titled('Long name')+"document.querySelector('#long').setAttribute('aria-label',"+inline(H1_NAME)+");"};
  return {body:'<main><h1>Hostile text</h1></main>',script:'const strings='+inline(HOSTILE)+',roles='+inline(H1_ROLES)+',main=document.querySelector("main");document.title=strings['+title+'];'
    +'const el=(tag,attributes={},text)=>{const node=document.createElement(tag);for(const [key,value]of Object.entries(attributes))node.setAttribute(key,value);if(text!==undefined)node.textContent=text;return node;};'
    +'strings.forEach((text,index)=>{const section=el("section",{"aria-label":text});section.append(el("h2",{},"Case "+index),el("button",{type:"button","aria-label":text}));'
    +'const value=el("textarea",{"aria-label":"Value "+index});value.defaultValue=text;'
    +'const list=el("select",{"aria-label":"List "+index});list.append(el("option",{value:"plain"},"Plain option"),el("option",{value:"hostile"},text));'
    +'const table=el("table",{"aria-label":"Table "+index}),head=el("tr"),row=el("tr");head.append(el("th",{},text),el("th",{},"Plain header"));row.append(el("td",{},"Plain cell"),el("td",{},text));table.append(head,row);'
    +'const checked=el("input",{"aria-label":"Checked "+index,"aria-invalid":"true","aria-describedby":"error-"+index});'
    +'section.append(value,list,table,checked,el("span",{id:"error-"+index},text),el("p",{},text));main.append(section);});'
    +'roles.forEach((role,index)=>{const node=el("div",{role,"aria-label":"Role "+index});node.append(document.createTextNode("Text "+index),el("button",{type:"button"},"Real "+index));main.append(node);});'};
}

// Group 14's addresses: one marker in every place a sign-in travels (the
// parameters code, access_token, sig and session; a random-looking value under
// an ordinary name; the fragment; a user name and password; a path segment
// after /reset/), beside an ordinary query that stays shown. It stands in link
// targets, a form's action and a frame's address; outline-read.mjs opens the
// page itself at an address that carries it too. mode=frame is the frame.
export const ADDRESS_MARK='Zq7Xk2Lm9Pw4Rt8Vb3Nc6Hd1Jf5Gs0Ya2Ue7Ko4i';
export const ADDRESS_QUERY='v=dQw4w9WgXcQ&q=red+shoes&page=2';
export const addressOf=(mark=ADDRESS_MARK)=>'http://fixture.test:8765/?case=efficiency-address&'+ADDRESS_QUERY+'&code='+mark+'&access_token='+mark+'&sig='+mark+'&session='+mark+'&ref='+mark+'#access_token='+mark;
export const ADDRESS_LINKS=[['Video link','/watch?'+ADDRESS_QUERY+'&sig='+ADDRESS_MARK],['Sign-in link','http://name:'+ADDRESS_MARK+'@fixture.test:8765/next?v=dQw4w9WgXcQ'],
  ['Reset link','/reset/'+ADDRESS_MARK+'?q=red+shoes'],['Fragment link','/x?page=2#ref='+ADDRESS_MARK],
  ['Token link','/t?access_token='+ADDRESS_MARK+'&session='+ADDRESS_MARK+'&code='+ADDRESS_MARK],['Random link','/r?ref='+ADDRESS_MARK]];
function address(mode){
  if(mode==='frame')return {body:'<p>Address frame text</p><a href="/frame-next?code='+ADDRESS_MARK+'">Frame marker link</a>',script:titled('Address frame')};
  return {body:'<h1>Address fixture</h1>'+ADDRESS_LINKS.map(([name,href])=>'<p><a href="'+escape(href)+'">'+name+'</a></p>').join('')
    +'<form aria-label="Marker form" method="get" action="'+escape('/receive?case=efficiency-address-form&session='+ADDRESS_MARK+'&'+ADDRESS_QUERY)+'"><label>Query <input name="query"></label><button type="submit">Search</button></form>'
    +'<iframe title="Marker frame" src="'+escape('/?case=efficiency-address&mode=frame&code='+ADDRESS_MARK+'&ref='+ADDRESS_MARK)+'"></iframe>',script:titled('Address fixture')};
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
  if(name==='f6')return f6(url.searchParams.get('mode'));
  if(name==='h1')return h1(url.searchParams.get('mode'),Math.max(0,Math.min(HOSTILE.length-1,Number.parseInt(url.searchParams.get('title')||'0',10)||0)));
  if(name==='address')return address(url.searchParams.get('mode'));
  if(name==='tab')return {body:'<p>'+escape(tabTitle(id))+'</p>',script:titled(tabTitle(id))};
  return null;
}
