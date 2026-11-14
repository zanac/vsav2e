-- logs the 68000's writes to the QSound shared RAM during the ending (mode ff8004 = 0x0a)
local cpu=manager.machine.devices[':maincpu']
local space=cpu.spaces['program']
local log={} local active=false
qtap=space:install_write_tap(0x618000,0x619fff,'q',function(offset,data,mask)
  if active then log[#log+1]=string.format('%d %06x %04x %04x', manager.machine.screens[':screen']:frame_number(), offset, data, mask) end
  return data end)
local done=false
function on_frame2(f)
  local mode=space:read_u16(0xff8004)
  if mode==0x0a and not active and not done then active=true end
  if active and mode~=0x0a then
    done=true; active=false
    local fh=io.open(os.getenv('TRACE_OUT')..'/qwrites.txt','w')
    for _,l in ipairs(log) do fh:write(l..'\n') end
    fh:close(); manager.machine:exit()
  end
end
local fh=io.open("/tmp/claude-0/vs/lua/drive.lua"); local src=fh:read("a"); fh:close(); load(src,"drive","t",_ENV)()
