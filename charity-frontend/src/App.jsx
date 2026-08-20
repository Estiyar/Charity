import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import Footer from './components/Footer'
import Header from './components/Header'
import CreateCard from './pages/author/CreateCard'
import AuthorFundraiserDetail from './pages/author/AuthorFundraiserDetail'
import AuthorFundraisers from './pages/author/AuthorFundraisers'
import AuthorBeneficiaries from './pages/author/AuthorBeneficiaries'
import AuthorLayout from './pages/author/AuthorLayout'
import AuthorProfile from './pages/author/AuthorProfile'
import Profile from './pages/Profile'
import UserProfile from './pages/UserProfile'
import DonorCabinetPanel from './components/DonorCabinetPanel'
import CardDetail from './pages/CardDetail'
import Catalog from './pages/Catalog'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import ModeratorLayout from './pages/moderator/ModeratorLayout'
import ModeratorList from './pages/moderator/ModeratorList'
import ManualReviewQueue from './pages/moderator/ManualReviewQueue'
import ManualReviewDetail from './pages/moderator/ManualReviewDetail'
import AdminCards from './pages/admin/AdminCards'
import AdminDonations from './pages/admin/AdminDonations'
import AdminExpenses from './pages/admin/AdminExpenses'
import AdminLayout from './pages/admin/AdminLayout'
import AdminModerators from './pages/admin/AdminModerators'
import AdminReferences from './pages/admin/AdminReferences'
import AdminRiskConfig from './pages/admin/AdminRiskConfig'
import AdminSettings from './pages/admin/AdminSettings'
import AdminUsers from './pages/admin/AdminUsers'
import ModeratorExpenseReview from './pages/moderator/ModeratorExpenseReview'
import ModeratorInvoiceReview from './pages/moderator/ModeratorInvoiceReview'
import ModeratorReview from './pages/moderator/ModeratorReview'
import ModeratorRepresentations from './pages/moderator/ModeratorRepresentations'
import ModeratorReports from './pages/moderator/ModeratorReports'
import PaymentResult from './pages/PaymentResult'
import DevCheckout from './pages/DevCheckout'
import DonorDashboard from './pages/donor/DonorDashboard'
import Notifications from './pages/Notifications'

export default function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/cards/:id" element={<CardDetail />} />
          <Route path="/payments/result" element={<PaymentResult />} />
          <Route path="/payments/dev-checkout/:paymentId" element={<DevCheckout />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/profile"
            element={(
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            )}
          />
          <Route path="/profile/:userId" element={<UserProfile />} />
          <Route
            path="/notifications"
            element={(
              <ProtectedRoute>
                <Notifications />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/author"
            element={(
              <ProtectedRoute role="author">
                <AuthorLayout />
              </ProtectedRoute>
            )}
          >
            <Route index element={<AuthorFundraisers />} />
            <Route path="beneficiaries" element={<AuthorBeneficiaries />} />
            <Route path="cards/:id" element={<AuthorFundraiserDetail />} />
            <Route path="donor" element={<DonorCabinetPanel showProfile={false} />} />
          </Route>
          <Route
            path="/author/create"
            element={(
              <ProtectedRoute role="author">
                <CreateCard />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/author/profile"
            element={(
              <ProtectedRoute role="author">
                <AuthorProfile />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/donor"
            element={(
              <ProtectedRoute role="donor">
                <DonorDashboard />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/admin"
            element={(
              <ProtectedRoute role="admin">
                <AdminLayout />
              </ProtectedRoute>
            )}
          >
            <Route index element={<AdminUsers />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="cards" element={<AdminCards />} />
            <Route path="moderators" element={<AdminModerators />} />
            <Route path="donations" element={<AdminDonations />} />
            <Route path="expenses" element={<AdminExpenses />} />
            <Route path="references" element={<AdminReferences />} />
            <Route path="risk-config" element={<AdminRiskConfig />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
          <Route
            path="/moderator"
            element={(
              <ProtectedRoute role="moderator">
                <ModeratorLayout />
              </ProtectedRoute>
            )}
          >
            <Route index element={<ModeratorList status="pending_moderation" title="Новые заявки" />} />
            <Route path="reviews" element={<ManualReviewQueue />} />
            <Route path="reviews/:id" element={<ManualReviewDetail />} />
            <Route path="representations" element={<ModeratorRepresentations />} />
            <Route path="reports" element={<ModeratorReports />} />
            <Route path="revision" element={<ModeratorList status="revision_required" title="На доработке" />} />
            <Route path="approved" element={<ModeratorList status="active" title="Одобренные" />} />
            <Route path="rejected" element={<ModeratorList status="rejected" title="Отклонённые" />} />
            <Route
              path="documents"
              element={<ModeratorList documentsMode title="Документы на проверке" />}
            />
            <Route
              path="expenses"
              element={<ModeratorList expensesMode title="Расходы на проверке" />}
            />
            <Route path="expenses/:id" element={<ModeratorExpenseReview />} />
            <Route
              path="invoices"
              element={<ModeratorList invoicesMode title="Счета клиникам" />}
            />
            <Route path="invoices/:id" element={<ModeratorInvoiceReview />} />
            <Route path="cards/:id" element={<ModeratorReview />} />
          </Route>
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
