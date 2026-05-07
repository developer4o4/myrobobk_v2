math.randomseed(os.time())

request = function()
    local telegram_id = math.random(100000, 999999999) -- 6–9 digit

    local body = '{"telegram_id": ' .. telegram_id .. '}'

    return wrk.format("POST", nil, {
        ["Content-Type"] = "application/json"
    }, body)
end
