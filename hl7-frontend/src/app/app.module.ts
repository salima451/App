import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { NgApexchartsModule } from 'ng-apexcharts';

// Composants principaux
import { AppComponent } from './app.component';
import { LoginComponent } from './login/login.component';
import{ParcoursComponent} from './parcourspatient/parcourspatient.component'
// Routes Angular
import { routes } from './app.routes';
import { ScrollingModule } from '@angular/cdk/scrolling';
@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    ParcoursComponent,
    
    // 🔜 Ajoute ici RegisterComponent, DashboardComponent, PatientJourneyComponent, etc.
  ],
  imports: [
    BrowserModule,
    FormsModule, // ⚠️ important pour [(ngModel)]
    HttpClientModule,
    ScrollingModule,
    NgApexchartsModule, 
    RouterModule.forRoot(routes) // configuration du routage
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
