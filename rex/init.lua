-- Herdr keys, from ~/.config/herdr-app/keys.json and ~/.config/herdr/config.toml.
-- A Herdr "space" is a Rex session. Keys Rex already shares with Herdr
-- (cmd+t, cmd+d, cmd+shift+d, cmd+p, cmd+1..9, cmd+alt+arrows, ...) are left alone.

-- Direct shortcuts where Rex's defaults differ from Herdr
rex.bind("cmd+w", "client.tab.close")    -- Rex default closes the pane first
rex.bind("cmd+shift+w", "pane.close")    -- Rex default closes the window
rex.bind("cmd+n", "session.new")         -- Rex default opens a new window
rex.bind("cmd+alt+]", "session.next")
rex.bind("cmd+alt+[", "session.previous")
rex.bind("cmd+b", "client.sidebar.toggle")
rex.bind("f2", "client.tab.rename")
rex.bind("shift+f2", "session.rename")
rex.bind("cmd+/", "client.palette.toggle")       -- Herdr: help. Rex default toggles the sidebar (cmd+b does that now)
rex.bind("cmd+shift+/", "client.palette.toggle")

-- ctrl+1..9 jumps to a session by number, like Herdr's space.select.
-- Sessions are numbered by creation time.
rex.action{
  name = "herdr_session_goto",
  title = "Go to Session by Number",
  category = "Session",
  args = { index = "integer" },
  run = function(ctx, args)
    local res, err = rex.call("session.list")
    if not res then error(err) end
    local ids = {}
    for _, s in ipairs(res.sessions) do
      table.insert(ids, s.session_id)
    end
    table.sort(ids) -- session IDs are UUIDv7, so they sort by creation time
    local id = ids[args.index]
    if id then
      rex.client.queue("session.select", { session_id = id })
    end
  end,
}
for i = 1, 9 do
  rex.bind("ctrl+" .. i, "herdr_session_goto", { index = i })
end

-- Prefix keys (ctrl+f, then the key), from the Herdr app keys.json.
-- Keys marked "TUI extra" come from the Herdr TUI (config.toml); the Herdr
-- app does not have them.
local P = "ctrl+f>"

-- ctrl+f twice sends a real ctrl+f to the terminal (nvim page down).
rex.bind(P .. "ctrl+f", "pane.send_key", { key = "ctrl+f" })

rex.bind(P .. "shift+/", "client.palette.toggle") -- Herdr: help
rex.bind(P .. "s", "client.settings")
rex.bind(P .. "w", "session.switch")              -- workspace picker
rex.bind(P .. "g", "pane.go_to")                  -- TUI extra: goto
rex.bind(P .. "shift+r", "client.config.reload")  -- TUI extra

-- Sessions (Herdr spaces)
rex.bind(P .. "shift+n", "session.new")
rex.bind(P .. "shift+w", "session.rename")
rex.bind(P .. "shift+d", "session.close")

-- Tabs
rex.bind(P .. "c", "client.tab.new")
rex.bind(P .. "shift+t", "client.tab.rename")
rex.bind(P .. "n", "client.tab.next")
rex.bind(P .. "p", "client.tab.previous")
rex.bind(P .. "shift+x", "client.tab.close")
for i = 1, 9 do
  rex.bind(P .. i, "client.tab.goto", { index = i })
end

-- Panes
rex.bind(P .. "h", "pane.focus.left")
rex.bind(P .. "j", "pane.focus.down")
rex.bind(P .. "k", "pane.focus.up")
rex.bind(P .. "l", "pane.focus.right")
rex.bind(P .. "tab", "pane.focus_next")            -- TUI extra
rex.bind(P .. "shift+tab", "pane.focus_previous") -- TUI extra
rex.bind(P .. "v", "pane.split.right")
rex.bind(P .. "-", "pane.split.down")
-- ctrl+f x closes the pane. On the last pane in the tab, pane.close does
-- nothing, so close the whole tab instead.
rex.action{
  name = "herdr_pane_close",
  title = "Close Pane, or Tab if Last Pane",
  category = "Pane",
  run = function(ctx)
    local view, err = rex.call("session.view", { session_id = ctx.session_id })
    if not view then error(err) end

    -- Find the tab holding the pane the key was pressed in. Fall back to the
    -- active tab if Rex didn't pass a pane.
    local tab
    for _, w in ipairs(view.windows or {}) do
      if ctx.block_id == nil and w.window_id == view.active_window_id then
        tab = w
      end
      for _, layer in ipairs(w.layers or {}) do
        for _, b in ipairs(layer.blocks or {}) do
          if b.block_id == ctx.block_id then tab = w end
        end
      end
    end

    -- Count panes across every layer, floating ones included.
    local panes = 0
    for _, layer in ipairs(tab and tab.layers or {}) do
      panes = panes + #(layer.blocks or {})
    end

    if panes <= 1 then
      rex.client.queue("client.tab.close", {})
    else
      rex.client.queue("pane.close", {})
    end
  end,
}
rex.bind(P .. "x", "herdr_pane_close")
rex.bind(P .. "z", "pane.zoom")
rex.bind(P .. "shift+p", "pane.rename")           -- TUI extra
rex.bind(P .. "b", "client.sidebar.toggle")

-- TUI extra. Resize mode: ctrl+f r, then h/j/k/l or arrows. Escape or enter leaves.
rex.bind(P .. "r", "client.mode.enter", { name = "resize" })
for key, dir in pairs{ h = "left", j = "down", k = "up", l = "right",
                       left = "left", down = "down", up = "up", right = "right" } do
  rex.bind("resize/" .. key, "pane.resize", { direction = dir, amount = 5 })
end
rex.bind("resize/enter", "client.mode.exit")
