
import io, re
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st

APP_TITLE='Speechie Sidekick'; DATA_DIR=Path(__file__).parent/'data'
SESSION_COLUMNS=['student_id','student_initials','campus','date_of_service','service_type','minutes','attendance','note_status','billed','source','external_session_id','notes']
EVAL_COLUMNS=['student_id','student_initials','campus','eval_type','consent_or_referral_date','report_due_date','ard_due_date','parent_input','teacher_input','observation','testing','scores','draft','final','status','notes']
ARD_COLUMNS=['student_id','student_initials','campus','ard_type','meeting_date','goals_drafted','goals_shared_with_parents','parent_feedback_received','present_levels_updated','service_minutes_checked','teacher_input_reviewed','progress_data_ready','recommendations_ready','accommodations_reviewed','talking_points_ready','status','notes']
COSF_COLUMNS=['student_id','student_initials','campus','form_kind','start_or_exit_date','due_date','using_eval_data','teacher_info_collected','parent_info_collected','observation_data_collected','form_drafted','form_submitted','status','notes']
CALENDAR_COLUMNS=['date','is_school_day','label']

def style():
    st.set_page_config(page_title=APP_TITLE,page_icon='🌸',layout='wide')
    css = '''<style>.stApp{background:linear-gradient(180deg,#fff5fb,#fff 35%,#fff8fc)}section[data-testid="stSidebar"]{background:linear-gradient(180deg,#831843,#be185d)}section[data-testid="stSidebar"] *{color:white!important}.hero{padding:1.2rem 1.4rem;border-radius:28px;background:linear-gradient(135deg,#db2777,#fb7185,#f9a8d4);color:white;box-shadow:0 18px 40px rgba(219,39,119,.24);margin-bottom:1rem}.hero h1{margin:0;font-size:2.25rem;letter-spacing:-.04em}.hero p{margin:.35rem 0 0}.warn{padding:.8rem 1rem;border-radius:18px;background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12;margin-bottom:1rem}div[data-testid="stMetric"]{background:white;border:1px solid #fbcfe8;padding:1rem;border-radius:20px;box-shadow:0 10px 22px rgba(131,24,67,.06)}</style>'''
    st.markdown(css, unsafe_allow_html=True)

def hero(t,s): st.markdown(f'<div class="hero"><h1>{t}</h1><p>{s}</p></div>',unsafe_allow_html=True)
def safety(): st.markdown('<div class="warn"><b>Fake-data demo:</b> Do not enter real student/client info yet. Redaction is regex-only, not OpenAI Privacy Filter or HIPAA/FERPA de-identification.</div>',unsafe_allow_html=True)

def ensure():
    DATA_DIR.mkdir(exist_ok=True)
    for n,c in {'sessions.csv':SESSION_COLUMNS,'evals.csv':EVAL_COLUMNS,'ards.csv':ARD_COLUMNS,'cosf.csv':COSF_COLUMNS,'calendar.csv':CALENDAR_COLUMNS}.items():
        p=DATA_DIR/n
        if not p.exists(): pd.DataFrame(columns=c).to_csv(p,index=False)

def load(n,cols):
    ensure()
    try: df=pd.read_csv(DATA_DIR/n,dtype=str).fillna('')
    except Exception: df=pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df: df[c]=''
    return df[cols]
def save(n,df,cols):
    out=df.copy()
    for c in cols:
        if c not in out: out[c]=''
    out[cols].to_csv(DATA_DIR/n,index=False)

def pd_date(x):
    try: return pd.to_datetime(x).date() if str(x).strip() else None
    except Exception: return None
def iso(x):
    d=pd_date(x); return '' if d is None else d.isoformat()
def yes(x): return str(x).strip().lower() in ['yes','y','true','1','done','complete','completed','billed','submitted']
def yn(x): return 'Yes' if yes(x) else 'No'
def days_until(x):
    d=pd_date(x); return '' if d is None else (d-date.today()).days
def status_due(x,complete=False):
    if complete: return 'Complete'
    d=days_until(x)
    if d=='': return 'No date'
    return 'Overdue' if d<0 else ('Due soon' if d<=7 else 'On track')
def school_days_after(start,n,cal=None):
    d=pd_date(start)
    if d is None: return ''
    if cal is None or cal.empty:
        cur=d; count=0
        while count<n:
            cur+=timedelta(days=1)
            if cur.weekday()<5: count+=1
        return cur.isoformat()
    c=cal.copy(); c['date_obj']=pd.to_datetime(c['date'],errors='coerce').dt.date
    c=c[(c.date_obj>d)&(c.is_school_day.astype(str).str.lower().isin(['yes','true','1']))]
    ds=sorted(c.date_obj.dropna())
    return ds[n-1].isoformat() if len(ds)>=n else ''

def completed(row): return str(row.get('attendance','')).lower() in ['seen','makeup','present','attended','completed']
def bucket(row):
    if not completed(row): return 'Not billable / absent'
    if yes(row.get('billed','')): return 'Already billed'
    if str(row.get('note_status','')).lower() not in ['complete','completed','done','documented']: return 'Needs note'
    return 'Needs billing'
def enrich_sessions(df):
    if df.empty: return df.copy()
    out=df.copy(); out['billing_bucket']=out.apply(bucket,axis=1); out['date_obj']=pd.to_datetime(out.date_of_service,errors='coerce'); out['month']=out.date_obj.dt.to_period('M').astype(str); out['minutes_num']=pd.to_numeric(out.minutes,errors='coerce').fillna(0); return out

def editor(df,key,cols):
    e=st.data_editor(df,num_rows='dynamic',use_container_width=True,hide_index=True,key=key)
    for c in cols:
        if c not in e: e[c]=''
    return e[cols]
def dl(label,df,fn): st.download_button(label,df.to_csv(index=False).encode('utf-8'),fn,'text/csv')
def excel(sheets):
    b=io.BytesIO()
    with pd.ExcelWriter(b,engine='openpyxl') as w:
        for n,df in sheets.items(): df.to_excel(w,sheet_name=n[:31],index=False)
    return b.getvalue()

def nav():
    st.sidebar.markdown('## 🌸 Speechie Sidekick'); st.sidebar.caption('Cute SLP organization dashboard')
    return st.sidebar.radio('Go to',['🏠 Dashboard','🔎 Evaluations','💸 Billing','👧 Student History','📥 SLP Toolkit Import','📆 Weekly Closeout','🤝 ARD Prep','🌱 COSE/COSF','🛡️ Redaction','📤 Export','⚙️ Settings'])

def dashboard():
    hero('Speechie Sidekick','Pink, eval-first command center for school-based SLP organization.'); safety()
    s=enrich_sessions(load('sessions.csv',SESSION_COLUMNS)); e=load('evals.csv',EVAL_COLUMNS); a=load('ards.csv',ARD_COLUMNS); c=load('cosf.csv',COSF_COLUMNS)
    m=st.columns(5); m[0].metric('Evaluations',len(e)); m[1].metric('Sessions',len(s)); m[2].metric('Need billing',int((s.billing_bucket=='Needs billing').sum()) if not s.empty else 0); m[3].metric('Need notes',int((s.billing_bucket=='Needs note').sum()) if not s.empty else 0); m[4].metric('ARD/COSE',len(a)+len(c))
    l,r=st.columns([1.2,1])
    with l:
        st.markdown('### 🔎 Eval quick view')
        if e.empty: st.info('No evals yet.')
        else:
            v=e.copy()
            for col in ['parent_input','teacher_input','observation','testing','scores','draft','final']: v[col]=v[col].apply(lambda x:'✅' if yes(x) else '❌')
            st.dataframe(v[['student_id','student_initials','eval_type','report_due_date','ard_due_date','parent_input','teacher_input','observation','testing','scores','draft','final']],use_container_width=True,hide_index=True)
    with r:
        st.markdown('### 💸 Billing snapshot')
        if s.empty: st.info('No sessions yet.')
        else:
            cnt=s.billing_bucket.value_counts().reset_index(); cnt.columns=['Status','Count']; st.dataframe(cnt,use_container_width=True,hide_index=True)
    st.markdown('### This week'); weekly(inline=True)

def evaluations():
    hero('Evaluations','Compact eval tracker with work-back planning dates.'); safety(); df=load('evals.csv',EVAL_COLUMNS); cal=load('calendar.csv',CALENDAR_COLUMNS)
    with st.expander('Add evaluation',expanded=False):
        with st.form('add_eval',clear_on_submit=True):
            c1,c2,c3=st.columns(3); sid=c1.text_input('Student ID / alias'); init=c2.text_input('Initials'); campus=c3.text_input('Campus')
            c1,c2,c3=st.columns(3); etype=c1.selectbox('Eval type',['FIIE','Speech-only eval','Reevaluation','Pre-K eval','Other']); consent=c2.date_input('Consent/referral date',value=date.today()); auto=c3.checkbox('Auto-calc 45 school days',value=True)
            rep=school_days_after(consent,45,cal) if auto else date.today().isoformat(); ard=(pd_date(rep)+timedelta(days=30)).isoformat() if pd_date(rep) else ''; st.caption(f'Projected report due: {rep or "N/A"} | ARD due: {ard or "N/A"}')
            c1,c2,c3=st.columns(3); parent=c1.selectbox('Parent input?',['No','Yes']); teacher=c2.selectbox('Teacher input?',['No','Yes']); obs=c3.selectbox('Observation?',['No','Yes'])
            c1,c2,c3,c4=st.columns(4); testing=c1.selectbox('Testing?',['No','Yes']); scores=c2.selectbox('Scores?',['No','Yes']); draft=c3.selectbox('Draft?',['No','Yes']); final=c4.selectbox('Final?',['No','Yes'])
            status=st.selectbox('Status',['Not started','Waiting on forms','Testing','Drafting','Complete']); notes=st.text_area('Notes')
            if st.form_submit_button('Add eval',type='primary'):
                new=pd.DataFrame([{'student_id':sid,'student_initials':init,'campus':campus,'eval_type':etype,'consent_or_referral_date':consent.isoformat(),'report_due_date':rep,'ard_due_date':ard,'parent_input':parent,'teacher_input':teacher,'observation':obs,'testing':testing,'scores':scores,'draft':draft,'final':final,'status':status,'notes':notes}]); df=pd.concat([df,new],ignore_index=True); save('evals.csv',df,EVAL_COLUMNS); st.success('Eval added.')
    if not df.empty:
        v=df.copy(); v['days_until_report']=v.report_due_date.apply(days_until); v['deadline_status']=v.apply(lambda r:status_due(r.report_due_date,yes(r.final)),axis=1)
        for col in ['parent_input','teacher_input','observation','testing','scores','draft','final']: v[col]=v[col].apply(lambda x:'✅' if yes(x) else '❌')
        st.dataframe(v[['student_id','student_initials','eval_type','report_due_date','days_until_report','deadline_status','parent_input','teacher_input','observation','testing','scores','draft','final','status']],use_container_width=True,hide_index=True)
        st.markdown('### Work-back planner'); labels=[f'{r.student_id} - {r.student_initials} - {r.eval_type}' for r in df.itertuples()]; sel=st.selectbox('Choose eval',labels); row=df.iloc[labels.index(sel)]; due=pd_date(row.report_due_date)
        if due:
            plan=pd.DataFrame([('Send teacher forms',28),('Send parent forms',28),('Complete observation',21),('Complete testing',14),('Enter scores',10),('Draft report',7),('Final review',3),('Report due',0)],columns=['Task','days_before_due']); plan['Suggested due']=plan.days_before_due.apply(lambda x:(due-timedelta(days=int(x))).isoformat()); st.dataframe(plan[['Task','Suggested due']],use_container_width=True,hide_index=True)
    edited=editor(df,'eval_edit',EVAL_COLUMNS)
    if st.button('Save evaluations',type='primary'): save('evals.csv',edited,EVAL_COLUMNS); st.success('Saved.')
    dl('Download evaluations CSV',edited,'evaluations.csv')

def billing():
    hero('Billing','School-district billing view: sessions, billed, unbilled, and notes.'); safety(); df=enrich_sessions(load('sessions.csv',SESSION_COLUMNS))
    if df.empty: st.info('Import or add sessions first.'); return
    months=['All']+sorted([m for m in df.month.dropna().unique() if m!='NaT'],reverse=True); month=st.selectbox('Month',months); v=df if month=='All' else df[df.month==month]
    c=st.columns(4); c[0].metric('Sessions',len(v)); c[1].metric('Billed',int((v.billing_bucket=='Already billed').sum())); c[2].metric('Needs billing',int((v.billing_bucket=='Needs billing').sum())); c[3].metric('Needs note',int((v.billing_bucket=='Needs note').sum()))
    st.dataframe(v[['student_id','student_initials','campus','date_of_service','service_type','minutes','attendance','note_status','billed','billing_bucket','notes']],use_container_width=True,hide_index=True); dl('Download billing view CSV',v,'billing_view.csv')

def student_history():
    hero('Student History','Pull per-student session records quickly.'); safety(); df=enrich_sessions(load('sessions.csv',SESSION_COLUMNS))
    if df.empty: st.info('No sessions yet.'); return
    students=sorted((df.student_id+' - '+df.student_initials).unique()); sel=st.selectbox('Student',students); sid=sel.split(' - ')[0]; v=df[df.student_id==sid]
    c=st.columns(4); c[0].metric('Sessions',len(v)); c[1].metric('Minutes',int(v.minutes_num.sum())); c[2].metric('Billed',int((v.billing_bucket=='Already billed').sum())); c[3].metric('Unbilled/needs note',int(v.billing_bucket.isin(['Needs billing','Needs note']).sum()))
    st.dataframe(v[['date_of_service','service_type','minutes','attendance','note_status','billed','billing_bucket','notes']],use_container_width=True,hide_index=True); dl('Download student history CSV',v,f'{sid}_session_history.csv')

def slp_import():
    hero('SLP Toolkit Import','Upload exported session data and map columns into Speechie Sidekick.'); safety(); template=pd.DataFrame([{'Student':'S-001','Initials':'J.D.','School':'North Elementary','Session Date':'2026-08-24','Service':'Speech therapy','Minutes':'30','Status':'Seen','Documentation':'Complete','Billed':'No','Session ID':'fake-001','Comments':'Fake sample'}]); st.download_button('Download fake SLP Toolkit template',template.to_csv(index=False).encode('utf-8'),'fake_slp_toolkit_template.csv','text/csv')
    up=st.file_uploader('Upload SLP Toolkit CSV',type=['csv'])
    if up is None: return
    raw=pd.read_csv(up,dtype=str).fillna(''); st.dataframe(raw.head(25),use_container_width=True,hide_index=True); opts=['—']+list(raw.columns)
    defaults={'student_id':['Student','student_id','ID'],'student_initials':['Initials','Student Initials'],'campus':['School','Campus'],'date_of_service':['Session Date','Date','Service Date'],'service_type':['Service','Service Type'],'minutes':['Minutes','Duration'],'attendance':['Status','Attendance'],'note_status':['Documentation','Note Status'],'billed':['Billed','Billing Status'],'external_session_id':['Session ID','ID'],'notes':['Comments','Notes']}
    mapping={}; cols=st.columns(3)
    for i,target in enumerate(SESSION_COLUMNS):
        if target=='source': continue
        guess='—'
        for d in defaults.get(target,[]):
            if d in raw.columns: guess=d; break
        with cols[i%3]: mapping[target]=st.selectbox(target,opts,index=opts.index(guess) if guess in opts else 0)
    if st.button('Convert and save sessions',type='primary'):
        conv=pd.DataFrame(columns=SESSION_COLUMNS)
        for c in SESSION_COLUMNS: conv[c]='SLP Toolkit' if c=='source' else (raw[mapping[c]] if mapping.get(c) and mapping[c]!='—' else '')
        conv.date_of_service=conv.date_of_service.apply(iso); conv.billed=conv.billed.apply(yn); existing=load('sessions.csv',SESSION_COLUMNS); all_df=pd.concat([existing,conv],ignore_index=True).drop_duplicates(subset=['external_session_id','student_id','date_of_service'],keep='last'); save('sessions.csv',all_df,SESSION_COLUMNS); st.success(f'Imported {len(conv)} rows.'); st.dataframe(conv,use_container_width=True,hide_index=True)

def weekly(inline=False):
    if not inline: hero('Weekly Closeout','A simple weekly checklist so billing does not pile up.'); safety()
    df=enrich_sessions(load('sessions.csv',SESSION_COLUMNS))
    if df.empty: st.info('No sessions yet.'); return
    start=st.date_input('Week starting',value=date.today()-timedelta(days=date.today().weekday()),key='week_dash' if inline else 'week'); end=start+timedelta(days=6); v=df[(df.date_obj.dt.date>=start)&(df.date_obj.dt.date<=end)]
    c=st.columns(4); c[0].metric('Sessions',len(v)); c[1].metric('Billed',int((v.billing_bucket=='Already billed').sum())); c[2].metric('Needs billing',int((v.billing_bucket=='Needs billing').sum())); c[3].metric('Needs notes',int((v.billing_bucket=='Needs note').sum()))
    if not inline: st.dataframe(v[['student_id','student_initials','date_of_service','minutes','note_status','billed','billing_bucket']],use_container_width=True,hide_index=True)

def ard_prep():
    hero('ARD Prep','Checklist aligned to her role, not facilitator backend tasks.'); safety(); df=load('ards.csv',ARD_COLUMNS); edited=editor(df,'ard_edit',ARD_COLUMNS)
    if st.button('Save ARD prep',type='primary'): save('ards.csv',edited,ARD_COLUMNS); st.success('Saved.')
    if not edited.empty:
        checks=[c for c in ARD_COLUMNS if c not in ['student_id','student_initials','campus','ard_type','meeting_date','status','notes']]; v=edited.copy(); v['missing_items']=v[checks].apply(lambda r:', '.join([c for c in checks if not yes(r[c])]),axis=1); st.dataframe(v[['student_id','student_initials','ard_type','meeting_date','missing_items','status']],use_container_width=True,hide_index=True)
    dl('Download ARD CSV',edited,'ard_prep.csv')

def cosf():
    hero('COSE/COSF','Pre-K entry/exit form tracker with 30-day due date support.'); safety(); df=load('cosf.csv',COSF_COLUMNS)
    with st.expander('Add COSE/COSF item',expanded=False):
        with st.form('add_cosf',clear_on_submit=True):
            c1,c2,c3=st.columns(3); sid=c1.text_input('Student ID'); init=c2.text_input('Initials'); campus=c3.text_input('Campus'); c1,c2,c3=st.columns(3); kind=c1.selectbox('Form kind',['Entry','Exit']); start=c2.date_input('Start/exit date',value=date.today()); due=c3.date_input('Due date',value=start+timedelta(days=30)); evaldata=st.selectbox('Using eval data?',['No','Yes']); teach=st.selectbox('Teacher info?',['No','Yes']); parent=st.selectbox('Parent info?',['No','Yes']); obs=st.selectbox('Observation data?',['No','Yes']); draft=st.selectbox('Form drafted?',['No','Yes']); sub=st.selectbox('Submitted?',['No','Yes']); status=st.selectbox('Status',['Not started','In progress','Complete']); notes=st.text_area('Notes')
            if st.form_submit_button('Add',type='primary'):
                new=pd.DataFrame([{'student_id':sid,'student_initials':init,'campus':campus,'form_kind':kind,'start_or_exit_date':start.isoformat(),'due_date':due.isoformat(),'using_eval_data':evaldata,'teacher_info_collected':teach,'parent_info_collected':parent,'observation_data_collected':obs,'form_drafted':draft,'form_submitted':sub,'status':status,'notes':notes}]); df=pd.concat([df,new],ignore_index=True); save('cosf.csv',df,COSF_COLUMNS)
    edited=editor(df,'cosf_edit',COSF_COLUMNS)
    if st.button('Save COSE/COSF',type='primary'): save('cosf.csv',edited,COSF_COLUMNS); st.success('Saved.')
    if not edited.empty:
        v=edited.copy(); v['days_remaining']=v.due_date.apply(days_until); v['deadline_status']=v.apply(lambda r:status_due(r.due_date,yes(r.form_submitted)),axis=1); st.dataframe(v[['student_id','student_initials','form_kind','start_or_exit_date','due_date','days_remaining','deadline_status','form_submitted','status']],use_container_width=True,hide_index=True)

def redact_text(txt,custom):
    out=txt or ''
    for t in custom:
        if t.strip(): out=re.sub(re.escape(t.strip()),'[REDACTED]',out,flags=re.I)
    for p,r in [(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b','[NAME]'),(r'\b[\w\.-]+@[\w\.-]+\.\w+\b','[EMAIL]'),(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b','[PHONE]'),(r'\b\d{2}/\d{2}/\d{4}\b','[DATE]'),(r'\b\d{4}-\d{2}-\d{2}\b','[DATE]')]: out=re.sub(p,r,out)
    return out

def redaction():
    hero('Redaction','Upload or paste text, add custom names, preview and download a redacted copy.'); safety(); terms=[x.strip() for x in st.text_input('Custom terms to redact, comma-separated').split(',') if x.strip()]; up=st.file_uploader('Upload .txt file for demo redaction',type=['txt']); txt=''
    if up: txt=up.read().decode('utf-8',errors='ignore')
    txt=st.text_area('Or paste fake sample text',value=txt,height=220)
    if st.button('Redact',type='primary'):
        red=redact_text(txt,terms); st.text_area('Redacted output',value=red,height=220); st.download_button('Download redacted text',red.encode('utf-8'),'redacted.txt','text/plain')

def export_page():
    hero('Export','Download consolidated workbook.'); safety(); s=enrich_sessions(load('sessions.csv',SESSION_COLUMNS)); e=load('evals.csv',EVAL_COLUMNS); a=load('ards.csv',ARD_COLUMNS); c=load('cosf.csv',COSF_COLUMNS); st.download_button('Download Excel packet',excel({'Sessions':s,'Evaluations':e,'ARD Prep':a,'COSE_COSF':c}),'speechie_sidekick_packet.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary')

def settings():
    hero('Settings','Academic calendar upload and next steps.'); safety(); st.markdown('### Academic calendar'); st.caption('Upload CSV with columns: date, is_school_day, label. Used for eval due-date calculations.'); up=st.file_uploader('Upload calendar CSV',type=['csv'])
    if up:
        cal=pd.read_csv(up,dtype=str).fillna('')
        for col in CALENDAR_COLUMNS:
            if col not in cal: cal[col]=''
        save('calendar.csv',cal,CALENDAR_COLUMNS); st.success('Calendar saved.')
    cal=load('calendar.csv',CALENDAR_COLUMNS); edited=editor(cal,'cal_edit',CALENDAR_COLUMNS)
    if st.button('Save calendar',type='primary'): save('calendar.csv',edited,CALENDAR_COLUMNS); st.success('Saved.')
    st.markdown('### Coming later'); st.write('- Eval-writing assistant from her examples.'); st.write('- Handwritten assessment extraction with confirmation before interpretation.'); st.write('- IPA/articulation helper.'); st.write('- OpenAI Privacy Filter/local redaction upgrade.')

def main():
    style(); ensure(); page=nav()
    {'🏠 Dashboard':dashboard,'🔎 Evaluations':evaluations,'💸 Billing':billing,'👧 Student History':student_history,'📥 SLP Toolkit Import':slp_import,'📆 Weekly Closeout':weekly,'🤝 ARD Prep':ard_prep,'🌱 COSE/COSF':cosf,'🛡️ Redaction':redaction,'📤 Export':export_page,'⚙️ Settings':settings}[page]()
if __name__=='__main__': main()
