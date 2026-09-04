1// src/pages/profile.tsx
import { useState, useRef, useEffect } from 'react';
import { withAuth } from '@/hoc/withAuth';
import { useAuthStore } from '@/store/useAuthStore';
import { 
  User, 
  Mail, 
  Phone, 
  MapPin, 
  Briefcase, 
  Building2, 
  Clock, 
  Edit2, 
  Camera, 
  Save, 
  X,
  Bell,
  Moon,
  Sun,
  Monitor,
  Globe,
  LayoutGrid,
  List,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import Link from 'next/link';

function ProfilePage() {
  const { user, setUser, logout } = useAuthStore();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    bio: '',
    department: '',
    position: '',
    phone: '',
    location: '',
    timezone: '',
    preferences: {
      theme: 'light' as 'light' | 'dark' | 'system',
      notifications: true,
      emailNotifications: true,
      language: 'en',
      dashboardView: 'grid' as 'grid' | 'list',
    }
  });

  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  // Load user data
  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name || '',
        email: user.email || '',
        bio: user.bio || '',
        department: user.department || '',
        position: user.position || '',
        phone: user.phone || '',
        location: user.location || '',
        timezone: user.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        preferences: {
          theme: user.preferences?.theme || 'light',
          notifications: user.preferences?.notifications !== false,
          emailNotifications: user.preferences?.emailNotifications !== false,
          language: user.preferences?.language || 'en',
          dashboardView: user.preferences?.dashboardView || 'grid',
        }
      });
      if (user.avatar) {
        setAvatarPreview(user.avatar);
      }
    }
  }, [user]);

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Image size should be less than 5MB');
        return;
      }
      if (!file.type.startsWith('image/')) {
        toast.error('Please upload an image file');
        return;
      }
      setAvatarFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setAvatarPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name.includes('.')) {
      const [parent, child] = name.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...(prev as any)[parent],
          [child]: value === 'true' ? true : value === 'false' ? false : value
        }
      }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    if (name.includes('.')) {
      const [parent, child] = name.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...(prev as any)[parent],
          [child]: checked
        }
      }));
    }
  };

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) return;
    
    setIsSaving(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Update user in store
      if (user) {
        const updatedUser = {
          ...user,
          name: formData.name,
          email: formData.email,
          bio: formData.bio,
          department: formData.department,
          position: formData.position,
          phone: formData.phone,
          location: formData.location,
          timezone: formData.timezone,
          preferences: formData.preferences,
          avatar: avatarPreview || user.avatar,
        };
        setUser(updatedUser);
      }
      
      toast.success('Profile updated successfully! 🎉');
      setIsEditing(false);
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (user) {
      setFormData({
        name: user.name || '',
        email: user.email || '',
        bio: user.bio || '',
        department: user.department || '',
        position: user.position || '',
        phone: user.phone || '',
        location: user.location || '',
        timezone: user.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        preferences: {
          theme: user.preferences?.theme || 'light',
          notifications: user.preferences?.notifications !== false,
          emailNotifications: user.preferences?.emailNotifications !== false,
          language: user.preferences?.language || 'en',
          dashboardView: user.preferences?.dashboardView || 'grid',
        }
      });
      setAvatarPreview(user.avatar || null);
      setAvatarFile(null);
    }
    setIsEditing(false);
    setErrors({});
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  const timezones = [
    'UTC', 'America/New_York', 'America/Los_Angeles', 'Europe/London', 
    'Europe/Paris', 'Asia/Dubai', 'Asia/Kolkata', 'Asia/Tokyo', 
    'Australia/Sydney', 'Pacific/Auckland'
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 sm:py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-3">
            👤 Profile
            <span className="text-sm font-normal text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              {user.role}
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage your account settings and preferences
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="btn btn-primary flex items-center gap-2"
            >
              <Edit2 className="w-4 h-4" />
              Edit Profile
            </button>
          )}
        </div>
      </div>

      {/* Profile Card */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-soft border border-gray-200/60 overflow-hidden">
        {/* Cover & Avatar */}
        <div className="relative">
          {/* Cover */}
          <div className="h-32 sm:h-40 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500" />
          
          {/* Avatar */}
          <div className="absolute -bottom-12 left-6 sm:left-8">
            <div className="relative group">
              <div className="w-24 h-24 rounded-full border-4 border-white bg-white shadow-lg overflow-hidden">
                {avatarPreview ? (
                  <img
                    src={avatarPreview}
                    alt={user.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-100 to-indigo-100 text-4xl font-bold text-blue-600">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              {isEditing && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute bottom-0 right-0 p-1.5 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                >
                  <Camera className="w-4 h-4" />
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleAvatarChange}
                className="hidden"
              />
            </div>
          </div>

          {/* Edit/Save buttons - moved to top right */}
          <div className="absolute top-3 right-3 flex items-center gap-2">
            {isEditing && (
              <>
                <button
                  onClick={handleCancel}
                  className="px-3 py-1.5 text-sm bg-white/90 backdrop-blur-sm text-gray-700 rounded-lg hover:bg-white transition-colors shadow-sm flex items-center gap-1.5"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isSaving ? (
                    <>
                      <span className="spinner-sm" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Save
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Profile Info */}
        <div className="pt-16 px-6 pb-6">
          {/* Name & Role */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div>
              {isEditing ? (
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  className={`text-xl font-bold text-gray-900 border rounded-xl px-3 py-1.5 w-full sm:w-64 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all ${
                    errors.name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Your name"
                />
              ) : (
                <h2 className="text-xl font-bold text-gray-900">{user.name}</h2>
              )}
              {errors.name && (
                <p className="mt-1 text-xs text-red-500">{errors.name}</p>
              )}
              <p className="text-sm text-gray-500 mt-0.5">
                {user.email} · Member since {format(new Date(user.createdAt), 'MMM d, yyyy')}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                user.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
              }`}>
                {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
              </span>
              {user.lastLogin && (
                <span className="text-xs text-gray-400">
                  Last login: {format(new Date(user.lastLogin), 'MMM d, h:mm a')}
                </span>
              )}
            </div>
          </div>

          {/* Profile Form */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {/* Bio */}
            <div className="md:col-span-2">
              <label className="text-sm font-medium text-gray-700 block mb-1">Bio</label>
              {isEditing ? (
                <textarea
                  name="bio"
                  value={formData.bio}
                  onChange={handleInputChange}
                  rows={3}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="Tell us about yourself..."
                />
              ) : (
                <p className="text-sm text-gray-600">{formData.bio || 'No bio provided'}</p>
              )}
            </div>

            {/* Department */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                <Building2 className="w-4 h-4 inline mr-1.5" />
                Department
              </label>
              {isEditing ? (
                <input
                  type="text"
                  name="department"
                  value={formData.department}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="e.g., Engineering"
                />
              ) : (
                <p className="text-sm text-gray-600">{formData.department || 'Not specified'}</p>
              )}
            </div>

            {/* Position */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                <Briefcase className="w-4 h-4 inline mr-1.5" />
                Position
              </label>
              {isEditing ? (
                <input
                  type="text"
                  name="position"
                  value={formData.position}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="e.g., Senior Engineer"
                />
              ) : (
                <p className="text-sm text-gray-600">{formData.position || 'Not specified'}</p>
              )}
            </div>

            {/* Phone */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                <Phone className="w-4 h-4 inline mr-1.5" />
                Phone
              </label>
              {isEditing ? (
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="+1 234 567 890"
                />
              ) : (
                <p className="text-sm text-gray-600">{formData.phone || 'Not specified'}</p>
              )}
            </div>

            {/* Location */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                <MapPin className="w-4 h-4 inline mr-1.5" />
                Location
              </label>
              {isEditing ? (
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="City, Country"
                />
              ) : (
                <p className="text-sm text-gray-600">{formData.location || 'Not specified'}</p>
              )}
            </div>

            {/* Timezone */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                <Clock className="w-4 h-4 inline mr-1.5" />
                Timezone
              </label>
              {isEditing ? (
                <select
                  name="timezone"
                  value={formData.timezone}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                >
                  {timezones.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              ) : (
                <p className="text-sm text-gray-600">{formData.timezone}</p>
              )}
            </div>
          </div>

          {/* Preferences Section */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Bell className="w-4 h-4" />
              Preferences
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Theme */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Theme</label>
                {isEditing ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        preferences: { ...prev.preferences, theme: 'light' }
                      }))}
                      className={`flex-1 px-3 py-2 rounded-lg border transition-all flex items-center justify-center gap-1.5 ${
                        formData.preferences.theme === 'light' 
                          ? 'border-blue-500 bg-blue-50 text-blue-700' 
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <Sun className="w-4 h-4" />
                      Light
                    </button>
                    <button
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        preferences: { ...prev.preferences, theme: 'dark' }
                      }))}
                      className={`flex-1 px-3 py-2 rounded-lg border transition-all flex items-center justify-center gap-1.5 ${
                        formData.preferences.theme === 'dark' 
                          ? 'border-blue-500 bg-blue-50 text-blue-700' 
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <Moon className="w-4 h-4" />
                      Dark
                    </button>
                    <button
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        preferences: { ...prev.preferences, theme: 'system' }
                      }))}
                      className={`flex-1 px-3 py-2 rounded-lg border transition-all flex items-center justify-center gap-1.5 ${
                        formData.preferences.theme === 'system' 
                          ? 'border-blue-500 bg-blue-50 text-blue-700' 
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <Monitor className="w-4 h-4" />
                      System
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 capitalize">{formData.preferences.theme}</p>
                )}
              </div>

              {/* Dashboard View */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Dashboard View</label>
                {isEditing ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        preferences: { ...prev.preferences, dashboardView: 'grid' }
                      }))}
                      className={`flex-1 px-3 py-2 rounded-lg border transition-all flex items-center justify-center gap-1.5 ${
                        formData.preferences.dashboardView === 'grid' 
                          ? 'border-blue-500 bg-blue-50 text-blue-700' 
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <LayoutGrid className="w-4 h-4" />
                      Grid
                    </button>
                    <button
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        preferences: { ...prev.preferences, dashboardView: 'list' }
                      }))}
                      className={`flex-1 px-3 py-2 rounded-lg border transition-all flex items-center justify-center gap-1.5 ${
                        formData.preferences.dashboardView === 'list' 
                          ? 'border-blue-500 bg-blue-50 text-blue-700' 
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <List className="w-4 h-4" />
                      List
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 capitalize">{formData.preferences.dashboardView}</p>
                )}
              </div>

              {/* Notifications */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Notifications</label>
                {isEditing ? (
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        name="preferences.notifications"
                        checked={formData.preferences.notifications}
                        onChange={handleCheckboxChange}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-600">Push notifications</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        name="preferences.emailNotifications"
                        checked={formData.preferences.emailNotifications}
                        onChange={handleCheckboxChange}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-600">Email notifications</span>
                    </label>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-sm text-gray-600">
                      Push: {formData.preferences.notifications ? '✅ On' : '❌ Off'}
                    </p>
                    <p className="text-sm text-gray-600">
                      Email: {formData.preferences.emailNotifications ? '✅ On' : '❌ Off'}
                    </p>
                  </div>
                )}
              </div>

              {/* Language */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  <Globe className="w-4 h-4 inline mr-1.5" />
                  Language
                </label>
                {isEditing ? (
                  <select
                    name="preferences.language"
                    value={formData.preferences.language}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="hi">Hindi</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                  </select>
                ) : (
                  <p className="text-sm text-gray-600">
                    {formData.preferences.language === 'en' ? 'English' : 
                     formData.preferences.language === 'es' ? 'Spanish' :
                     formData.preferences.language === 'fr' ? 'French' :
                     formData.preferences.language === 'de' ? 'German' :
                     formData.preferences.language === 'hi' ? 'Hindi' :
                     formData.preferences.language === 'zh' ? 'Chinese' :
                     formData.preferences.language === 'ja' ? 'Japanese' :
                     formData.preferences.language}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Account Actions */}
          <div className="mt-6 pt-4 border-t border-gray-200 flex flex-wrap items-center justify-between gap-4">
            <div className="text-xs text-gray-400">
              <p>Account created: {format(new Date(user.createdAt), 'MMM d, yyyy h:mm a')}</p>
              {user.lastLogin && (
                <p>Last login: {format(new Date(user.lastLogin), 'MMM d, yyyy h:mm a')}</p>
              )}
            </div>
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to logout?')) {
                  logout();
                }
              }}
              className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default withAuth(ProfilePage);