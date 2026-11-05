"""Retry ordinary fast-forward Git push only for explicit transient server/transport errors."""
import subprocess,sys,time
branch=sys.argv[1]
transient=('internal server error','fatal error in commit_refs','http 500','http 502','http 503','http 504','connection reset','remote end hung up','timed out')
for attempt in range(4):
 p=subprocess.run(['git','push','origin','HEAD:'+branch],capture_output=True,text=True);message=p.stdout+p.stderr;print(message,flush=True)
 if p.returncode==0:break
 bad=('non-fast-forward','fetch first','permission denied','protected branch','authentication failed','not permitted','access denied')
 if attempt==3 or any(x in message.lower() for x in bad) or not any(x in message.lower() for x in transient):raise SystemExit(p.returncode)
 time.sleep(5*(attempt+1))
