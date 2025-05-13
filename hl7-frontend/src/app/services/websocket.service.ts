import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { bufferTime, filter } from 'rxjs/operators';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class WebSocketService {
  private wsSubject: WebSocketSubject<any> = webSocket('ws://localhost:8080'); // adapte l'URL

  public getBufferedStream(): Observable<any[]> {
    return this.wsSubject.pipe(
      bufferTime(200),
      filter(batch => batch.length > 0)
    );
  }
}
