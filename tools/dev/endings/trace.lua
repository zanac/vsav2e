-- CPS2 tile-usage tracer: TRACE_OUT dir; BIN frames per bin; writes bins as lines "frame tiles..."
local out=os.getenv('TRACE_OUT')
local BIN=tonumber(os.getenv('BIN') or '30')
local LAST=tonumber(os.getenv('LAST') or '3600')
local sh=manager.machine.memory.shares
local o1,o2,ga,gr=sh[':objram1'],sh[':objram2'],sh[':cps_a_regs'],sh[':gfxram']
local f=0
local used={}
local usedS={}
local fh=io.open(out..'/bins.txt','w')
local function objs(ram)
  for i=0,8192-8,8 do
    local x=ram:read_u16(i); local y=ram:read_u16(i+2)
    local code=ram:read_u16(i+4); local attr=ram:read_u16(i+6)
    if y>=0x8000 or attr>=0xff00 then break end
    code=code+((y&0x6000)<<3)
    local nx=((attr>>8)&15)+1; local ny=((attr>>12)&15)+1
    if attr&0xff00==0 then nx=1; ny=1 end
    for a=0,ny-1 do for b=0,nx-1 do usedS[(code+b+16*a)&0x3ffff]=true end end
  end
end
local function scroll(reg,kind)
  local base=(ga:read_u16(reg*2)*256)&~(0x4000-1)&0x3ffff
  if base>=196608-0x4000 then return end
  for i=0,0x4000-4,4 do
    local code=gr:read_u16(base+i)
    if kind==1 then used[((code+0x20000)>>1)&0x3ffff]=true
    elseif kind==2 then used[(code+0x10000)&0x3ffff]=true
    else local t=((code+0x4000)*4)&0x3ffff; used[t]=true; used[t+1]=true; used[t+2]=true; used[t+3]=true end
  end
end
local hooks={}
emu.register_frame_done(function()
  f=f+1
  if on_frame then on_frame(f) end
  objs(o1); objs(o2)
  if f%3==0 then scroll(1,1); scroll(2,2); scroll(3,3) end
  if f%BIN==0 then
    local t={}
    for k,_ in pairs(used) do t[#t+1]=string.format('%x',k) end
    local u={}
    for k,_ in pairs(usedS) do u[#u+1]=string.format('%x',k) end
    fh:write(f..' S '..table.concat(u,' ')..'\n'..f..' B '..table.concat(t,' ')..'\n'); fh:flush(); used={}; usedS={}
  end
  if f>=LAST then fh:close(); manager.machine:exit() end
end)
