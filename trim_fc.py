if second == -1:> 
    raise SystemExit('no duplicate') 
path.write_text(text[:second].rstrip() + '\n', encoding='utf-8') 
text = path.read_text(encoding='utf-8') 
needle = 'from main_model import DataModel' 
first = text.find(needle) 
if first == -1: 
    raise SystemExit('needle not found') 
second = text.find(needle, first + len(needle)) 
if second == -1: 
    raise SystemExit('no duplicate') 
path.write_text(text[:second].rstrip() + '\n', encoding='utf-8') 
