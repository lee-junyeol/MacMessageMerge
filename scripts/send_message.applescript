on run argv
    set targetAddress to item 1 of argv
    set messageText to item 2 of argv
    set focusTrace to ""

    try
        tell application "Messages" to activate
        delay 0.7

        tell application "System Events"
            if UI elements enabled is false then
                error "손쉬운 사용(UI 자동화) 권한이 필요합니다. 시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용에서 Terminal(또는 이 앱을 실행한 프로그램)을 허용해주세요." number 10001
            end if

            tell process "Messages"
                set frontmost to true

                -- 매 수신자마다 반드시 새 메시지 작성에서 시작한다.
                keystroke "n" using command down
                delay 0.75

                -- 수신번호는 클립보드를 사용하지 않고 직접 입력한다.
                -- Python에서 숫자와 +만 남긴 값이 전달된다.
                keystroke targetAddress
                delay 0.35
                key code 36 -- Return: 수신자 후보/번호 확정
                delay 0.85

                set bodyReady to false
                set bodyElement to missing value
                set frontWindow to front window
                set winPos to position of frontWindow
                set winSize to size of frontWindow
                set winX to item 1 of winPos
                set winY to item 2 of winPos
                set winW to item 1 of winSize
                set winH to item 2 of winSize
                set lowerBoundary to winY + (winH * 0.32)

                -- 1차: Tab 이동으로 실제 하단 텍스트 입력 요소를 찾는다.
                repeat with i from 1 to 8
                    key code 48 -- Tab
                    delay 0.16
                    try
                        set focusedElement to value of attribute "AXFocusedUIElement"
                        set focusedRole to value of attribute "AXRole" of focusedElement
                        set focusedPos to position of focusedElement
                        set focusedY to item 2 of focusedPos
                        set focusTrace to focusTrace & "TAB" & i & ":" & focusedRole & "@" & (focusedY as integer) & ";"

                        if ((focusedRole is "AXTextArea") or (focusedRole is "AXTextField")) and focusedY > lowerBoundary then
                            set bodyReady to true
                            set bodyElement to focusedElement
                            exit repeat
                        end if
                    on error
                        set focusTrace to focusTrace & "TAB" & i & ":?;"
                    end try
                end repeat

                -- 2차: Accessibility 트리에서 하단 텍스트 입력 요소를 직접 찾는다.
                if bodyReady is false then
                    set bestElement to missing value
                    set bestY to -1
                    try
                        set allElements to entire contents of frontWindow
                        repeat with elementRef in allElements
                            try
                                set candidateElement to contents of elementRef
                                set candidateRole to value of attribute "AXRole" of candidateElement
                                if (candidateRole is "AXTextArea") or (candidateRole is "AXTextField") then
                                    set candidatePos to position of candidateElement
                                    set candidateSize to size of candidateElement
                                    set candidateX to item 1 of candidatePos
                                    set candidateY to item 2 of candidatePos
                                    set candidateW to item 1 of candidateSize
                                    set candidateH to item 2 of candidateSize

                                    if candidateY > lowerBoundary and candidateX > (winX + (winW * 0.18)) and candidateW > 80 and candidateH > 18 then
                                        set focusTrace to focusTrace & "CAND:" & candidateRole & "@" & (candidateX as integer) & "," & (candidateY as integer) & ";"
                                        if candidateY > bestY then
                                            set bestY to candidateY
                                            set bestElement to candidateElement
                                        end if
                                    end if
                                end if
                            end try
                        end repeat
                    end try

                    if bestElement is not missing value then
                        try
                            set bestPos to position of bestElement
                            set bestSize to size of bestElement
                            set clickX to (item 1 of bestPos) + 20
                            set clickY to (item 2 of bestPos) + ((item 2 of bestSize) / 2)
                            click at {clickX, clickY}
                            delay 0.2

                            set focusedElement to value of attribute "AXFocusedUIElement"
                            set focusedRole to value of attribute "AXRole" of focusedElement
                            set focusedPos to position of focusedElement
                            set focusedY to item 2 of focusedPos
                            set focusTrace to focusTrace & "AXCLICK:" & focusedRole & "@" & (focusedY as integer) & ";"
                            if ((focusedRole is "AXTextArea") or (focusedRole is "AXTextField")) and focusedY > lowerBoundary then
                                set bodyReady to true
                                set bodyElement to focusedElement
                            end if
                        end try
                    end if
                end if

                -- 3차: 일반적인 Messages 하단 작성영역을 클릭한 뒤 다시 검증한다.
                if bodyReady is false then
                    try
                        set fallbackX to winX + (winW * 0.68)
                        set fallbackY to winY + winH - 58
                        click at {fallbackX, fallbackY}
                        delay 0.2

                        set focusedElement to value of attribute "AXFocusedUIElement"
                        set focusedRole to value of attribute "AXRole" of focusedElement
                        set focusedPos to position of focusedElement
                        set focusedY to item 2 of focusedPos
                        set focusTrace to focusTrace & "FALLBACK:" & focusedRole & "@" & (focusedY as integer) & ";"
                        if ((focusedRole is "AXTextArea") or (focusedRole is "AXTextField")) and focusedY > lowerBoundary then
                            set bodyReady to true
                            set bodyElement to focusedElement
                        end if
                    end try
                end if

                if bodyReady is false or bodyElement is missing value then
                    error "새 메시지는 열었지만 메시지 입력칸을 찾지 못했습니다. 포커스 진단: " & focusTrace number 10002
                end if

                -- 핵심: Command-V/클립보드를 사용하지 않는다.
                -- Accessibility의 AXValue에 Unicode 본문을 직접 넣는다.
                try
                    set value of attribute "AXValue" of bodyElement to messageText
                on error errMsg
                    error "메시지 입력칸에 텍스트를 직접 설정하지 못했습니다: " & errMsg number 10004
                end try
                delay 0.2

                -- 실제 본문이 들어갔는지 확인한다. 확인되지 않으면 절대 전송하지 않는다.
                try
                    set insertedText to value of attribute "AXValue" of bodyElement
                    if insertedText is missing value then
                        error "본문 입력 후 AXValue를 읽을 수 없습니다." number 10005
                    end if
                    if (insertedText as text) is not messageText then
                        error "본문 입력 검증에 실패했습니다. 파일/다른 데이터가 입력되는 것을 막기 위해 전송을 중단합니다." number 10005
                    end if
                on error errMsg number errNum
                    if errNum is 10005 then error errMsg number 10005
                    error "본문 입력 상태를 검증하지 못했습니다: " & errMsg number 10005
                end try

                -- 전송 직전에도 현재 포커스가 텍스트 입력 요소인지 확인한다.
                set focusedElement to value of attribute "AXFocusedUIElement"
                set focusedRole to value of attribute "AXRole" of focusedElement
                if (focusedRole is not "AXTextArea") and (focusedRole is not "AXTextField") then
                    -- AXValue는 이미 올바른 본문 요소에 설정되었으므로 해당 요소를 다시 클릭한다.
                    try
                        set bodyPos to position of bodyElement
                        set bodySize to size of bodyElement
                        click at {(item 1 of bodyPos) + 20, (item 2 of bodyPos) + ((item 2 of bodySize) / 2)}
                        delay 0.15
                        set focusedElement to value of attribute "AXFocusedUIElement"
                        set focusedRole to value of attribute "AXRole" of focusedElement
                    end try
                end if

                if (focusedRole is not "AXTextArea") and (focusedRole is not "AXTextField") then
                    error "메시지 입력 직전에 작성창 포커스를 잃었습니다. 현재 역할: " & focusedRole number 10003
                end if

                key code 36 -- Return: 전송
                delay 0.65
            end tell
        end tell

        return "SUCCESS"

    on error errMsg number errNum
        return "ERROR: " & errMsg & " (Code: " & errNum & ")"
    end try
end run