-- Chạy các lệnh này trong Supabase SQL Editor

-- Bảng users (profile)
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng logo_sets
CREATE TABLE logo_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_logo TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng logos
CREATE TABLE logos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    logo_set_id UUID REFERENCES logo_sets(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id_prefix TEXT NOT NULL,
    url TEXT NOT NULL
);

-- Bảng history
CREATE TABLE history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    accountid TEXT,
    start_time TEXT,
    end_time TEXT,
    background TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng notifications
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    duration INTEGER DEFAULT 5,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Storage buckets (tạo trong Supabase Dashboard > Storage)
-- Tạo bucket tên "logos" (public)
-- Tạo bucket tên "history" (public)

-- Set admin đầu tiên (thay YOUR_USER_ID bằng UUID của bạn)
-- UPDATE users SET role = 'admin' WHERE id = 'YOUR_USER_ID';
