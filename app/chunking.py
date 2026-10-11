

def chunk_text(text: str, size: int = 120, overlap: int = 20) -> list[str]:

    words = text.split()
    step = size - overlap
    chunks = []

    for start in range(0,len(words),step):
        piece = words[start:start + size]
        if piece:
            chunks.append(piece)
        
        if start + size >= len(words):
            break
    return chunks