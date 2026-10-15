import {
  Award, BookOpen, Building2, CalendarDays, CalendarRange, ClipboardCheck,
  ContactRound, FileChartColumn, GraduationCap, History, LayoutDashboard,
  LibraryBig, Link2, MessageCircle, NotebookPen, Presentation, School,
  Search, ShieldCheck, TableProperties, UserRound, UserRoundPen,
} from "lucide-react";

// Different destinations have distinct symbols. Reuse a module's symbol wherever
// that same destination appears, so navigation, shortcuts and cards agree.
export const moduleIcons = {
  search: Search,
  dashboard: LayoutDashboard,
  students: GraduationCap,
  guardians: ContactRound,
  "guardian-links": Link2,
  teachers: Presentation,
  "academic-years": CalendarDays,
  "academic-terms": CalendarRange,
  subjects: BookOpen,
  curricula: LibraryBig,
  "curriculum-subjects": TableProperties,
  classes: School,
  assignments: UserRoundPen,
  enrollments: ClipboardCheck,
  learning: NotebookPen,
  annual: Award,
  whatsapp: MessageCircle,
  exports: FileChartColumn,
  audit: History,
  accounts: ShieldCheck,
  institutions: Building2,
  portal: UserRound,
} as const;
