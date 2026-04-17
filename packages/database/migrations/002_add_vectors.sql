-- 002_add_vectors.sql
-- Vector embeddings for semantic search
-- NOTE: Requires pgvector extension. Falls back gracefully if not available.

DO
$$

BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
    
    ALTER TABLE grants ADD COLUMN IF NOT EXISTS embedding vector(384);
    ALTER TABLE organizations ADD COLUMN IF NOT EXISTS mission_embedding vector(384);
    
    -- IVFFlat index for fast vector search
    CREATE INDEX IF NOT EXISTS idx_grants_embedding 
        ON grants USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50);
    
    RAISE NOTICE 'pgvector extension and indexes created successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pgvector not available — vector search will use fallback. Error: %', SQLERRM;
        -- Add embedding as JSONB array fallback
        ALTER TABLE grants ADD COLUMN IF NOT EXISTS embedding_json JSONB;
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS mission_embedding_json JSONB;
END
$$;
