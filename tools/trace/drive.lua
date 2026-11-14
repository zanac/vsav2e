-- input driver: PRESS="frame:port:field;..." (held 4 frames), SHOTS, DUMPS (RAM 0xff0000), then trace
local ports=manager.machine.ioport.ports
local prog=manager.machine.devices[':maincpu'].spaces['program']
local out=os.getenv('TRACE_OUT')
local press={}
for fr,pt,fl in (os.getenv('PRESS') or ''):gmatch('(%d+):([^:;]+):([^;]+)') do press[#press+1]={tonumber(fr),pt,fl} end
local shots={} for n in (os.getenv('SHOTS') or ''):gmatch('%d+') do shots[tonumber(n)]=true end
local gfx_dumps={} for n in (os.getenv('GDUMPS') or ''):gmatch('%d+') do gfx_dumps[tonumber(n)]=true end
local dumps={} for n in (os.getenv('DUMPS') or ''):gmatch('%d+') do dumps[tonumber(n)]=true end
local pokes={} for fr,fr2,a,v in (os.getenv('POKES') or ''):gmatch('(%d+)-(%d+):(%x+):(%x+)') do pokes[#pokes+1]={tonumber(fr),tonumber(a,16),tonumber(v,16),tonumber(fr2)} end
local held={}
local mash=tonumber(os.getenv('MASH') or '-1')
local mf={'P1 Left','P1 Right','P1 Up','P1 Down','P1 Button 1','P1 Button 2','P1 Button 3'}
local mf2={'P1 Button 4','P1 Button 5','P1 Button 6'}
math.randomseed(tonumber(os.getenv('SEED') or '1',16) or 1)
local mstate={}
function on_frame(f)
  if f==650 then print("on_frame 650") end
  for _,p in ipairs(press) do
    local fld=ports[':'..p[2]].fields[p[3]]
    if f==p[1] then fld:set_value(1) elseif f==p[1]+4 then fld:set_value(0) end
  end
  if mash>=0 and f>=mash and f%6==0 then
    for _,n in ipairs(mf) do ports[':IN0'].fields[n]:set_value(math.random()<0.3 and 1 or 0) end
    for _,n in ipairs(mf2) do ports[':IN1'].fields[n]:set_value(math.random()<0.25 and 1 or 0) end
  end
  if os.getenv('AUTOWIN') and f>=1700 then
    prog:write_u16(0xff8450,288); prog:write_u16(0xff8452,288)
    if f%120==0 then prog:write_u16(0xff8850,0); prog:write_u16(0xff8852,0) end
  end
  for _,p in ipairs(pokes) do if f>=p[1] and f<=p[4] then prog:write_u8(p[2],p[3]) end end
  -- GDUMPS: the CPS2 graphics RAM (scroll layers and palettes), 0x900000-0x92ffff
  if gfx_dumps[f] then local fh=io.open(out..'/gfxram_'..f..'.bin','wb'); fh:write(prog:read_range(0x900000,0x92ffff,8)); fh:close() end
  if dumps[f] then local fh=io.open(out..'/ram_'..f..'.bin','wb'); fh:write(prog:read_range(0xff0000,0xffffff,8)); fh:close() end
  if shots[f] then manager.machine.video:snapshot(); os.rename(out..'/'..manager.machine.system.name..'/0000.png',out..string.format('/f%06d.png',f)) end
  if on_frame2 then on_frame2(f) end
end
local fh=io.open((os.getenv("VS_TOOLS") or ".").."/trace.lua"); local src=fh:read("a"); fh:close(); load(src,"trace","t",_ENV)()
