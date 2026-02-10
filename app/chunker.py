# app/chunker.py - ПРОСТОЙ, НАДЕЖНЫЙ и УЧИТЫВАЮЩИЙ АБЗАЦЫ
def semantic_chunk(text, max_chunk_size=2000, overlap=200):
    """
    Чанкинг с приоритетом:
    1. Если текст короче max_chunk_size → один чанк
    2. Иначе — разбивка с учётом абзацев, предложений и перекрытия
    """
    if not text or max_chunk_size <= 0:
        return []

    text = text.strip()
    if not text:
        return []

    text_length = len(text)

    # Короткий текст → один чанк
    if text_length <= max_chunk_size:
        return [(text, 0, text_length)]

    # Нормализуем overlap
    if overlap >= max_chunk_size:
        overlap = max_chunk_size // 4

    # ... остальной код без изменений ...
    
    chunks = []
    text_length = len(text)
    step = max_chunk_size - overlap
    
    if step <= 0:
        step = max_chunk_size // 2
    
    start = 0
    iteration = 0
    max_iterations = (text_length // step) * 2

    while start < text_length and iteration < max_iterations:
        end = min(start + max_chunk_size, text_length)
        
        if end < text_length:
            best_end = end
            
            # 1. Ищем границу абзаца в пределах окна (приоритет!)
            for pos in range(end, max(start, end - 300), -1):
                if pos > start and text[pos-1:pos+1] == '\n\n':
                    best_end = pos
                    break
            else:
                # 2. Если нет абзаца — ищем конец предложения
                for pos in range(end, max(start, end - 150), -1):
                    if text[pos-1] in '.!?;…':
                        best_end = pos
                        break
                else:
                    # 3. Если нет предложения — ищем пробел (слово)
                    for pos in range(end, max(start, end - 50), -1):
                        if text[pos-1] == ' ':
                            best_end = pos
                            break
            
            end = best_end
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((chunk_text, start, end))
        
        # Сдвигаем с учётом перекрытия
        start = end - overlap
        if start < 0:
            start = 0
        if start >= end:  # защита от зацикливания
            start = end + 1
        
        iteration += 1
    
    return chunks