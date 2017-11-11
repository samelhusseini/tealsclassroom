interface RemoteConfig {
    PUSHER_APP_KEY: string; // Pusher App Key
    iframeUrl: string; // Iframe URL to use in student view
    classSkype: string; // Classroom Skype session URL
}

interface RemoteSession {
    full_name: string;
    course_id: string;
    user_id: string;
    user_image: string;
    remote_link?: string;
    role?: string;
}

interface RemoteUser {
    studentId: string;
    fullName: string;
    avatarUrl: string;
    role: string;
    primaryRemoteLink: string;
    secondaryRemoteLink: string;
}