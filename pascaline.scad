/* PASCALINE V0.2 — mm — rigid pivot pawls, metal guides, indexed release.
   Independent manufacturing objects use Z >= 0; each OBJ is one solid.
   External metal tubes, bolts, spring ball plungers and return springs REQUIRED.
   Assembly poses prescribe motion; physical friction/fatigue not simulated.
*/
// @export base 1
// @export digit_wheel 2
// @export units_cam 1
// @export carry_slider 1
// @export drive_pawl 1
// @export stop_pawl 2
// @export shaft_spacer 2
// @export upper_spacer 2
// @export top_cover 1

part="assembly";
units_angle=0;
tens_angle=0;
show_cover=false;
show_hardware=true;
$fn=96;
pitch=84;
base_width=188;
base_depth=104;
base_thickness=5;
wheel_radius=35;
ratchet_root_r=11.5;
ratchet_tip_r=17;
wheel_z=14;
pawl_z=14;
slider_z=6;
cam_z=6;
cam_thickness=4;
cam_base_r=22;
follower_r=1.5;
pawl_contact_r=12.5;
carry_stroke=10.4;
carry_low=-4.5;
carry_hold=8.3;
carry_peak_angle=350;
cam_samples=1440;
cover_z=26.5;
shaft_bore=4.2; // finish to measured OD + 0.10..0.15 mm if required
pivot_bore=4.2;
guide_slot_width=4.15; // FINISHED slot width: metal OD + 0.12..0.16 mm
guide_x=67;
guide_fixed_y=[-30,6]; // two points 36 mm apart along travel
guide_slot_y=[for(y=guide_fixed_y) y+(carry_stroke+carry_low)/2];
stop_rotation=-18;
stop_pivot=[-38,-13.5];
stop_bend=[-20,-20];
stop_end=[-3,-20];
stop_tail=[-45,-13.5];
stop_spring=[-41,-25];
drive_pivot=[48,22];
drive_end=[69.5,2];
drive_tail=[38,32];
drive_spring=[30,34];
arm_r=1.75;
stop_r=1.75;
open_angle=25;
drive_open_angle=15;
cam_pin_positions=[[-7,0],[5,5]];

function wrap(a)=(a%360+360)%360;
function ease(t)=t*t*(3-2*t);
function rot2(p,a)=[p[0]*cos(a)-p[1]*sin(a),p[0]*sin(a)+p[1]*cos(a)];
function unit(v)=v/norm(v);
function normal(v)=[-v[1],v[0]];
function closed_stop(p,e)=let(u=unit(e-p)) p+8*u+(arm_r+stop_r)*normal(u);
function opened_stop(p,e,a=open_angle)=let(u=rot2(unit(e-p),-a)) p+8*u-(arm_r+stop_r)*normal(u);
// Full carry is reached before 0, then the drive retreats to permit detent seating.
function cam_lift(a)=let(p=wrap(a))
 p<=36 ? carry_hold+(carry_low-carry_hold)*ease(p/36) :
 p<288 ? carry_low :
 p<324 ? carry_low*(1-ease((p-288)/36)) :
 p<=carry_peak_angle ? carry_stroke*ease((p-324)/(carry_peak_angle-324)) :
 carry_stroke+(carry_hold-carry_stroke)*ease((p-carry_peak_angle)/(360-carry_peak_angle));
function lift_derivative(a)=let(p=wrap(a))
 p<36 ? (carry_low-carry_hold)*6*(p/36)*(1-p/36)/(36*PI/180) :
 p<288 ? 0 :
 p<324 ? let(t=(p-288)/36) -carry_low*6*t*(1-t)/(36*PI/180) :
 p<carry_peak_angle ? let(t=(p-324)/(carry_peak_angle-324))
 carry_stroke*6*t*(1-t)/((carry_peak_angle-324)*PI/180) :
 let(t=(p-carry_peak_angle)/(360-carry_peak_angle))
 (carry_hold-carry_stroke)*6*t*(1-t)/((360-carry_peak_angle)*PI/180);
function cam_point(theta)=let(phase=wrap(270-theta),r=cam_base_r+follower_r+cam_lift(phase),
 rp=-lift_derivative(phase),n=[cos(theta),sin(theta)],t=[-sin(theta),cos(theta)],
 normal_v=(r*n-rp*t)/sqrt(r*r+rp*rp)) r*n-follower_r*normal_v;

module rounded_rect(w,h,r=3){hull() for(x=[-w/2+r,w/2-r],y=[-h/2+r,h/2-r])translate([x,y])circle(r=r);}
module link2(a,b,r){hull(){translate(a)circle(r=r);translate(b)circle(r=r);}}
module post_at(p,r,z,h){translate([p[0],p[1],z])cylinder(r=r,h=h);}
module hole_at(p,d,z,h){post_at(p,d/2,z,h);}
module cross_hole(p,z){translate([p[0]-4,p[1],z])rotate([0,90,0])cylinder(d=2.4,h=8);}

module base(){
 difference(){
  union(){
   translate([pitch/2,0,0])linear_extrude(5)rounded_rect(base_width,base_depth,5);
   // Solid pivot seats. Screws pass through and use nuts below; no resin threads.
   for(x=[0,pitch])translate([x,0,0])rotate([0,0,stop_rotation]){
    post_at(stop_pivot,6,5,9);
    // These bridges start above the cam; columns inside its sweep are avoided.
    for(s=[closed_stop(stop_pivot,stop_bend),opened_stop(stop_pivot,stop_bend)]){
     translate([0,0,11])linear_extrude(3)link2(stop_pivot,s,3);
     post_at(s,stop_r,14,3.5);
    }
    post_at(stop_spring,3,5,15);
   }
   // Ball-plunger mounts: bridge clears cam at Z=10 and ratchet R=17.
   for(x=[0,pitch]){
    post_at([x,42],6,5,9);
    translate([0,0,11])linear_extrude(7.5)link2([x,42],[x,29.5],6.5);
   }
   post_at([61,44],3,5,10);
   for(x=[-44,pitch+44],y=[-44,44])post_at([x,y],5,5,cover_z-5);
  }
  for(x=[0,pitch]){
   hole_at([x,0],3.4,-.1,5.2);
   // Metal axle tube seats one mm below top; finish seat to actual tube OD + .05.
   hole_at([x,0],4.05,4,1.1);
   translate([x,0,0])rotate([0,0,stop_rotation]){
    hole_at(stop_pivot,3.4,-.1,14.2);
    cross_hole(stop_spring,16.5);
   }
   hole_at([x,29.5],4.5,10.9,8);
   // Side-loaded M4 hex nut, AF7 + clearance, Z=14..17.5.
   translate([x,29.5,14])rotate([0,0,30])cylinder(d=8.55,h=3.5,$fn=6);
   translate([x-3.7,29.5,14])cube([7.4,14,3.5]);
  }
  for(y=guide_fixed_y)hole_at([guide_x,y],3.4,-.1,5.2);
  cross_hole([61,44],11.5);
  // Cover uses through bolts and nuts, not tapped slender resin posts.
  for(x=[-44,pitch+44],y=[-44,44])hole_at([x,y],3.4,-.1,cover_z+.2);
 }
}

module ratchet_profile(){polygon([for(k=[0:9])each[
 [ratchet_root_r*cos(36*k),ratchet_root_r*sin(36*k)],
 [ratchet_tip_r*cos(36*k),ratchet_tip_r*sin(36*k)],
 [ratchet_root_r*cos(36*(k+1)-1),ratchet_root_r*sin(36*(k+1)-1)]
 ]]);}
module digit_wheel(){
 difference(){
  union(){linear_extrude(4)ratchet_profile();cylinder(r=9,h=8);translate([0,0,7])cylinder(r=35,h=4);}
  cylinder(d=shaft_bore,h=11.1);
  for(p=cam_pin_positions)hole_at(p,3.8,-.1,3.7);
  for(k=[0:9])let(a=90-36*k){
   hole_at([23*cos(a),23*sin(a)],5.5,6.9,4.2);
   translate([29.3*cos(a),29.3*sin(a),10.25])rotate([0,0,a-90])
    linear_extrude(.85)text(str(k),size=4.5,halign="center",valign="center");
   // Open underside conical detent, not an internal void.
   translate([29.5*cos(a),29.5*sin(a),6.99])cylinder(d1=5.5,d2=.6,h=.61);
  }
 }
}
module digit_wheel_print(){translate([0,0,11])rotate([180,0,0])digit_wheel();}
module units_cam(){
 difference(){
  union(){
   linear_extrude(4)polygon([for(i=[0:cam_samples-1])cam_point(i*360/cam_samples)]);
   for(p=cam_pin_positions){
    hole_at(p,5.3,3.9,3.6); // top at assembly Z=13.5; wheel underside Z=14
    hole_at(p,3.4,3.9,7.1); // tip at assembly Z=17; 3 mm socket engagement
   }
  }
  cylinder(d=8.6,h=4.1);
  translate([0,15,3.5])linear_extrude(.6)text("U",size=4,halign="center",valign="center");
 }
}

module guide_slot(y){hull()for(dy=[-(carry_stroke-carry_low+1.2)/2,(carry_stroke-carry_low+1.2)/2])translate([guide_x,y+dy])circle(d=guide_slot_width);}
module carry_slider(){
 difference(){
  union(){
   translate([-3,-41,0])cube([76,4,3]);
   translate([61,-41,0])cube([12,73,3]);
   translate([-1.5,-41,0])cube([3,41-cam_base_r-follower_r,4]);
   hole_at([0,-cam_base_r-follower_r],3,0,4);
   for(y=guide_slot_y)translate([guide_x,y,0])linear_extrude(3)rounded_rect(12,26,2);
   translate([0,0,0])linear_extrude(3)link2([67,25],drive_pivot,5);
   post_at(drive_pivot,6,0,8);
   for(s=[closed_stop(drive_pivot,drive_end),opened_stop(drive_pivot,drive_tail,drive_open_angle)]){
    linear_extrude(8)link2(drive_pivot,s,3);
    post_at(s,stop_r,8,3.5);
   }
   linear_extrude(3)link2(drive_pivot,drive_spring,3);
   post_at(drive_spring,3,0,14);
   post_at([61,32],3,0,9);
  }
  for(y=guide_slot_y)translate([0,0,-.1])linear_extrude(3.2)guide_slot(y);
  hole_at(drive_pivot,3.4,-.1,8.2);
  // Side-loaded M3 nut. A top M3x12 button screw leaves its end above the slider bottom.
  translate([drive_pivot[0],drive_pivot[1],2])cylinder(d=6.7,h=2.7,$fn=6);
  translate([drive_pivot[0]-7,drive_pivot[1]-2.9,2])cube([7,5.8,2.7]);
  cross_hole(drive_spring,10.5);
  cross_hole([61,32],5.5);
 }
}
module drive_pawl(){
 difference(){
  linear_extrude(3)union(){
   translate(drive_pivot)circle(r=5.5);
   link2(drive_pivot,drive_end,arm_r);
   // Relieved trailing inner edge clears the preceding tooth during the push.
   polygon([[68,0],[71.5,0],[71,3.5],[68,3.5]]);
   link2(drive_pivot,drive_tail,arm_r);translate(drive_tail)circle(r=3);
  }
  hole_at(drive_pivot,pivot_bore,-.1,3.2);
  hole_at(drive_tail,2.4,-.1,3.2);
 }
}
module stop_pawl(){
 difference(){
  linear_extrude(3)union(){
   translate(stop_pivot)circle(r=5.5);
   link2(stop_pivot,stop_bend,arm_r);
   link2(stop_bend,stop_end,arm_r);
   translate([-3,-21.75])square([2.75,9.25]);
   link2(stop_pivot,stop_tail,arm_r);translate(stop_tail)circle(r=3);
  }
  hole_at(stop_pivot,pivot_bore,-.1,3.2);
  hole_at(stop_tail,2.4,-.1,3.2);
 }
}
module shaft_spacer(){difference(){union(){cylinder(d=12,h=1);cylinder(d=8,h=9);}cylinder(d=shaft_bore,h=9.1);}}
module upper_spacer(){difference(){cylinder(d=10,h=3.5);cylinder(d=shaft_bore,h=3.6);}}
module top_cover(){
 difference(){
  translate([pitch/2,0,0])linear_extrude(3)rounded_rect(base_width,base_depth,5);
  for(x=[0,pitch])hole_at([x,0],68,-.1,3.2);
  for(x=[-44,pitch+44],y=[-44,44])hole_at([x,y],3.4,-.1,3.2);
 }
 for(x=[0,pitch])translate([x,0,0])linear_extrude(3)polygon([[-3,36],[3,36],[0,32]]);
}
module tube(d,di,h){difference(){cylinder(d=d,h=h);cylinder(d=di,h=h+.1);}}
module hardware(){
 color([.55,.58,.62]){
  for(x=[0,pitch])translate([x,0,4])tube(4,3.2,25);
  for(y=guide_fixed_y){
   translate([67,y,5])tube(4,3.2,5);
   translate([67,y,5])tube(8,4.3,1);
   translate([67,y,9.2])tube(8,4.3,.8);
  }
  translate([drive_pivot[0],drive_pivot[1]-cam_lift(units_angle),14])tube(4,3.2,4);
  for(x=[0,pitch])translate([x,0,0])rotate([0,0,stop_rotation])translate([stop_pivot[0],stop_pivot[1],14])tube(4,3.2,4);
  for(x=[0,pitch]){
   post_at([x,29.5],2,12.85,8);
   translate([x,29.5,20.4])sphere(d=2.5); // free position; actual ball compresses in contact
  }
 }
}
module assembly(explode=0){
 color([.1,.35,.4])base();
 for(x=[0,pitch]){
  translate([x,0,5+explode*.2])shaft_spacer();
  translate([x,0,25+explode*1.1])upper_spacer();
  translate([x,0,14+explode*.6])rotate([0,0,stop_rotation])stop_pawl();
  translate([x,0,14+explode])rotate([0,0,x==0?units_angle:tens_angle])digit_wheel();
 }
 translate([0,0,cam_z+explode*.3])rotate([0,0,units_angle])units_cam();
 translate([0,-cam_lift(units_angle),slider_z+explode*.4])carry_slider();
 translate([0,-cam_lift(units_angle),pawl_z+explode*.6])drive_pawl();
 if(show_cover)translate([0,0,cover_z+explode*1.4])top_cover();
 if(show_hardware&&explode==0)hardware();
}
if(part=="assembly")assembly();
else if(part=="exploded")assembly(30);
else if(part=="base")base();
else if(part=="digit_wheel")digit_wheel_print();
else if(part=="units_cam")units_cam();
else if(part=="carry_slider")carry_slider();
else if(part=="drive_pawl")drive_pawl();
else if(part=="stop_pawl")stop_pawl();
else if(part=="shaft_spacer")shaft_spacer();
else if(part=="upper_spacer")upper_spacer();
else if(part=="top_cover")top_cover();
else assert(false,str("Unknown part: ",part));
